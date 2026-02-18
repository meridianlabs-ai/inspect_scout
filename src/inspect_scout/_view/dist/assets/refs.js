import { G as isMapOrSet, H as isFunction$1, N as NULL, I as isBigInt, J as error, K as isValid, L as getAggregate, M as walk, O as rowObjectCode, P as compile, Q as codegen, R as entries, S as parseExpression, T as isObject$1, U as is, V as Op, W as Column$1, X as Literal, Y as isNumber$1, Z as isString, _ as isArray, $ as toString, a0 as toArray, a1 as keyFunction, a2 as map_agg, a3 as entries_agg, a4 as object_agg, a5 as array_agg, a6 as isTypedArray, a7 as rowObjectBuilder, a8 as isArrayType, a9 as hasAggregate, aa as getWindow, ab as hasWindow, ac as array_agg_distinct, ad as any, ae as random, af as toNumber, ag as decodeUtf8$1, ah as bisect$1, ai as float64Array, aj as divide, ak as fromDecimal64, al as fromDecimal128, am as fromDecimal256, an as Type$2, ao as IntervalUnit$1, ap as invalidDataType, aq as TimeUnit$1, ar as DateUnit$1, as as encodeUtf8$1, at as grow, au as keyFor, av as CompressionType$1, aw as BodyCompressionMethod$1, ax as Version, ay as checkOneOf, az as union$1, aA as UnionMode$1, aB as mapType, aC as fixedSizeList, aD as fixedSizeBinary, aE as duration, aF as interval, aG as timestamp, aH as time, aI as date, aJ as decimal, aK as float, aL as Precision$1, aM as int, aN as runEndEncoded, aO as struct, aP as largeListView, aQ as largeList, aR as listView, aS as list, aT as largeUtf8, aU as largeBinary, aV as utf8, aW as binary, aX as dictionary$1, aY as int32$1, aZ as MessageHeader$1, a_ as isArrayBufferLike, a$ as MAGIC$1, b0 as int8Array, b1 as encodeMetadata, b2 as encodeSchema$1, b3 as EOS, b4 as uint8Array, b5 as align, b6 as keyString, b7 as nullType, b8 as isArray$1, b9 as float64$1, ba as bool, bb as dateDay, bc as field$1, bd as int8, be as int16, bf as int64, bg as toOffset, bh as toDecimal, bi as toMonthDayNanoBytes, bj as toBigInt, bk as toTimestamp, bl as toDateDay, bm as toDecimal32, bn as toFloat16, bo as isInt64ArrayType, bp as isIterable$1, bq as isTypedArray$1, br as uint64Array, bs as uint64, bt as uint32Array, bu as uint32, bv as uint16Array, bw as uint16, bx as uint8, by as int64Array, bz as int32Array, bA as int16Array, bB as float32Array, bC as float32$1, bD as Endianness$1, bE as isDate, bF as formatUTCDate, bG as formatDate, bH as count, bI as sequence, bJ as isRegExp, bK as lz4Exports, u as useApi, a as useAsyncDataFromQuery, y as skipToken, l as useStore, r as reactExports, t as toRelativePath, j as jsxRuntimeExports, g as clsx, bL as lib, bM as asyncJsonParse, x as data, e as ApplicationIcons, m as useSearchParams, s as scanResultRoute } from "./index.js";
import { a as useScanRoute } from "./useScansDir.js";
import { u as useMapAsyncData } from "./useMapAsyncData.js";
import { i as isJson, e as MarkdownDivWithReferences, R as RecordTree, u as useEventNodes, f as TranscriptViewNodes, g as ChatView } from "./TranscriptViewNodes.js";
import { p as printArray } from "./array.js";
import { f as formatPrettyDecimal } from "./ToolButton.js";
import { p as printObject } from "./object.js";
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
const decodeUtf8 = decoder.decode.bind(decoder);
const encoder = new TextEncoder();
const encodeUtf8 = (value2) => encoder.encode(value2);
const isNumber = (x) => typeof x === "number";
const isBoolean = (x) => typeof x === "boolean";
const isFunction = (x) => typeof x === "function";
const isObject = (x) => x != null && Object(x) === x;
const isPromise = (x) => {
  return isObject(x) && isFunction(x.then);
};
const isIterable = (x) => {
  return isObject(x) && isFunction(x[Symbol.iterator]);
};
const isAsyncIterable = (x) => {
  return isObject(x) && isFunction(x[Symbol.asyncIterator]);
};
const isArrowJSON = (x) => {
  return isObject(x) && isObject(x["schema"]);
};
const isIteratorResult = (x) => {
  return isObject(x) && "done" in x && "value" in x;
};
const isFileHandle = (x) => {
  return isObject(x) && isFunction(x["stat"]) && isNumber(x["fd"]);
};
const isFetchResponse = (x) => {
  return isObject(x) && isReadableDOMStream(x["body"]);
};
const isReadableInterop = (x) => "_getDOMStream" in x && "_getNodeStream" in x;
const isWritableDOMStream = (x) => {
  return isObject(x) && isFunction(x["abort"]) && isFunction(x["getWriter"]) && !isReadableInterop(x);
};
const isReadableDOMStream = (x) => {
  return isObject(x) && isFunction(x["cancel"]) && isFunction(x["getReader"]) && !isReadableInterop(x);
};
const isWritableNodeStream = (x) => {
  return isObject(x) && isFunction(x["end"]) && isFunction(x["write"]) && isBoolean(x["writable"]) && !isReadableInterop(x);
};
const isReadableNodeStream = (x) => {
  return isObject(x) && isFunction(x["read"]) && isFunction(x["pipe"]) && isBoolean(x["readable"]) && !isReadableInterop(x);
};
const isFlatbuffersByteBuffer = (x) => {
  return isObject(x) && isFunction(x["clear"]) && isFunction(x["bytes"]) && isFunction(x["position"]) && isFunction(x["setPosition"]) && isFunction(x["capacity"]) && isFunction(x["getBufferIdentifier"]) && isFunction(x["createLong"]);
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
function memcpy(target, source, targetByteOffset = 0, sourceByteLength = source.byteLength) {
  const targetByteLength = target.byteLength;
  const dst = new Uint8Array(target.buffer, target.byteOffset, targetByteLength);
  const src = new Uint8Array(source.buffer, source.byteOffset, Math.min(sourceByteLength, targetByteLength));
  dst.set(src, targetByteOffset);
  return target;
}
function joinUint8Arrays(chunks, size) {
  const result2 = collapseContiguousByteRanges(chunks);
  const byteLength = result2.reduce((x, b) => x + b.byteLength, 0);
  let source, sliced, buffer2;
  let offset = 0, index = -1;
  const length = Math.min(size || Number.POSITIVE_INFINITY, byteLength);
  for (const n = result2.length; ++index < n; ) {
    source = result2[index];
    sliced = source.subarray(0, Math.min(source.length, length - offset));
    if (length <= offset + sliced.length) {
      if (sliced.length < source.length) {
        result2[index] = source.subarray(sliced.length);
      } else if (sliced.length === source.length) {
        index++;
      }
      buffer2 ? memcpy(buffer2, sliced, offset) : buffer2 = sliced;
      break;
    }
    memcpy(buffer2 || (buffer2 = new Uint8Array(length)), sliced, offset);
    offset += sliced.length;
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
    value2 = encodeUtf8(value2);
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
function* toArrayBufferViewIterator(ArrayCtor, source) {
  const wrap2 = function* (x) {
    yield x;
  };
  const buffers = typeof source === "string" ? wrap2(source) : ArrayBuffer.isView(source) ? wrap2(source) : source instanceof ArrayBuffer ? wrap2(source) : source instanceof SharedArrayBuf ? wrap2(source) : !isIterable(source) ? wrap2(source) : source;
  yield* pump$1((function* (it) {
    let r = null;
    do {
      r = it.next(yield toArrayBufferView(ArrayCtor, r));
    } while (!r.done);
  })(buffers[Symbol.iterator]()));
  return new ArrayCtor();
}
const toUint8ArrayIterator = (input) => toArrayBufferViewIterator(Uint8Array, input);
function toArrayBufferViewAsyncIterator(ArrayCtor, source) {
  return __asyncGenerator(this, arguments, function* toArrayBufferViewAsyncIterator_1() {
    if (isPromise(source)) {
      return yield __await(yield __await(yield* __asyncDelegator(__asyncValues(toArrayBufferViewAsyncIterator(ArrayCtor, yield __await(source))))));
    }
    const wrap2 = function(x) {
      return __asyncGenerator(this, arguments, function* () {
        yield yield __await(yield __await(x));
      });
    };
    const emit = function(source2) {
      return __asyncGenerator(this, arguments, function* () {
        yield __await(yield* __asyncDelegator(__asyncValues(pump$1((function* (it) {
          let r = null;
          do {
            r = it.next(yield r === null || r === void 0 ? void 0 : r.value);
          } while (!r.done);
        })(source2[Symbol.iterator]())))));
      });
    };
    const buffers = typeof source === "string" ? wrap2(source) : ArrayBuffer.isView(source) ? wrap2(source) : source instanceof ArrayBuffer ? wrap2(source) : source instanceof SharedArrayBuf ? wrap2(source) : isIterable(source) ? emit(source) : !isAsyncIterable(source) ? wrap2(source) : source;
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
function rebaseValueOffsets(offset, length, valueOffsets) {
  if (offset !== 0) {
    valueOffsets = valueOffsets.slice(0, length);
    for (let i = -1, n = valueOffsets.length; ++i < n; ) {
      valueOffsets[i] += offset;
    }
  }
  return valueOffsets.subarray(0, length);
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
  fromIterable(source) {
    return pump(fromIterable$1(source));
  },
  fromAsyncIterable(source) {
    return pump(fromAsyncIterable(source));
  },
  fromDOMStream(source) {
    return pump(fromDOMStream(source));
  },
  fromNodeStream(stream) {
    return pump(fromNodeStream(stream));
  },
  // @ts-ignore
  toDOMStream(source, options) {
    throw new Error(`"toDOMStream" not available in this environment`);
  },
  // @ts-ignore
  toNodeStream(source, options) {
    throw new Error(`"toNodeStream" not available in this environment`);
  }
};
const pump = (iterator) => {
  iterator.next();
  return iterator;
};
function* fromIterable$1(source) {
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
  const it = toUint8ArrayIterator(source)[Symbol.iterator]();
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
function fromAsyncIterable(source) {
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
    const it = toUint8ArrayAsyncIterator(source)[Symbol.asyncIterator]();
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
function fromDOMStream(source) {
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
    const it = new AdaptiveByteReader(source);
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
      threw === false ? yield __await(it["cancel"]()) : source["locked"] && it.releaseLock();
    }
    return yield __await(null);
  });
}
class AdaptiveByteReader {
  constructor(source) {
    this.source = source;
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
      const { reader, source } = this;
      reader && (yield reader["cancel"](reason).catch(() => {
      }));
      source && (source["locked"] && this.releaseLock());
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
var UnionMode;
(function(UnionMode2) {
  UnionMode2[UnionMode2["Sparse"] = 0] = "Sparse";
  UnionMode2[UnionMode2["Dense"] = 1] = "Dense";
})(UnionMode || (UnionMode = {}));
var Precision;
(function(Precision2) {
  Precision2[Precision2["HALF"] = 0] = "HALF";
  Precision2[Precision2["SINGLE"] = 1] = "SINGLE";
  Precision2[Precision2["DOUBLE"] = 2] = "DOUBLE";
})(Precision || (Precision = {}));
var DateUnit;
(function(DateUnit2) {
  DateUnit2[DateUnit2["DAY"] = 0] = "DAY";
  DateUnit2[DateUnit2["MILLISECOND"] = 1] = "MILLISECOND";
})(DateUnit || (DateUnit = {}));
var TimeUnit;
(function(TimeUnit2) {
  TimeUnit2[TimeUnit2["SECOND"] = 0] = "SECOND";
  TimeUnit2[TimeUnit2["MILLISECOND"] = 1] = "MILLISECOND";
  TimeUnit2[TimeUnit2["MICROSECOND"] = 2] = "MICROSECOND";
  TimeUnit2[TimeUnit2["NANOSECOND"] = 3] = "NANOSECOND";
})(TimeUnit || (TimeUnit = {}));
var IntervalUnit;
(function(IntervalUnit2) {
  IntervalUnit2[IntervalUnit2["YEAR_MONTH"] = 0] = "YEAR_MONTH";
  IntervalUnit2[IntervalUnit2["DAY_TIME"] = 1] = "DAY_TIME";
  IntervalUnit2[IntervalUnit2["MONTH_DAY_NANO"] = 2] = "MONTH_DAY_NANO";
})(IntervalUnit || (IntervalUnit = {}));
const SIZEOF_SHORT$1 = 2;
const SIZEOF_INT$1 = 4;
const FILE_IDENTIFIER_LENGTH = 4;
const SIZE_PREFIX_LENGTH = 4;
const int32 = new Int32Array(2);
const float32 = new Float32Array(int32.buffer);
const float64 = new Float64Array(int32.buffer);
const isLittleEndian = new Uint16Array(new Uint8Array([1, 0]).buffer)[0] === 1;
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
  readInt8(offset) {
    return this.readUint8(offset) << 24 >> 24;
  }
  readUint8(offset) {
    return this.bytes_[offset];
  }
  readInt16(offset) {
    return this.readUint16(offset) << 16 >> 16;
  }
  readUint16(offset) {
    return this.bytes_[offset] | this.bytes_[offset + 1] << 8;
  }
  readInt32(offset) {
    return this.bytes_[offset] | this.bytes_[offset + 1] << 8 | this.bytes_[offset + 2] << 16 | this.bytes_[offset + 3] << 24;
  }
  readUint32(offset) {
    return this.readInt32(offset) >>> 0;
  }
  readInt64(offset) {
    return BigInt.asIntN(64, BigInt(this.readUint32(offset)) + (BigInt(this.readUint32(offset + 4)) << BigInt(32)));
  }
  readUint64(offset) {
    return BigInt.asUintN(64, BigInt(this.readUint32(offset)) + (BigInt(this.readUint32(offset + 4)) << BigInt(32)));
  }
  readFloat32(offset) {
    int32[0] = this.readInt32(offset);
    return float32[0];
  }
  readFloat64(offset) {
    int32[isLittleEndian ? 0 : 1] = this.readInt32(offset);
    int32[isLittleEndian ? 1 : 0] = this.readInt32(offset + 4);
    return float64[0];
  }
  writeInt8(offset, value2) {
    this.bytes_[offset] = value2;
  }
  writeUint8(offset, value2) {
    this.bytes_[offset] = value2;
  }
  writeInt16(offset, value2) {
    this.bytes_[offset] = value2;
    this.bytes_[offset + 1] = value2 >> 8;
  }
  writeUint16(offset, value2) {
    this.bytes_[offset] = value2;
    this.bytes_[offset + 1] = value2 >> 8;
  }
  writeInt32(offset, value2) {
    this.bytes_[offset] = value2;
    this.bytes_[offset + 1] = value2 >> 8;
    this.bytes_[offset + 2] = value2 >> 16;
    this.bytes_[offset + 3] = value2 >> 24;
  }
  writeUint32(offset, value2) {
    this.bytes_[offset] = value2;
    this.bytes_[offset + 1] = value2 >> 8;
    this.bytes_[offset + 2] = value2 >> 16;
    this.bytes_[offset + 3] = value2 >> 24;
  }
  writeInt64(offset, value2) {
    this.writeInt32(offset, Number(BigInt.asIntN(32, value2)));
    this.writeInt32(offset + 4, Number(BigInt.asIntN(32, value2 >> BigInt(32))));
  }
  writeUint64(offset, value2) {
    this.writeUint32(offset, Number(BigInt.asUintN(32, value2)));
    this.writeUint32(offset + 4, Number(BigInt.asUintN(32, value2 >> BigInt(32))));
  }
  writeFloat32(offset, value2) {
    float32[0] = value2;
    this.writeInt32(offset, int32[0]);
  }
  writeFloat64(offset, value2) {
    float64[0] = value2;
    this.writeInt32(offset, int32[isLittleEndian ? 0 : 1]);
    this.writeInt32(offset + 4, int32[isLittleEndian ? 1 : 0]);
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
  __union(t, offset) {
    t.bb_pos = offset + this.readInt32(offset);
    t.bb = this;
    return t;
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
  __string(offset, opt_encoding) {
    offset += this.readInt32(offset);
    const length = this.readInt32(offset);
    offset += SIZEOF_INT$1;
    const utf8bytes = this.bytes_.subarray(offset, offset + length);
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
  __union_with_string(o, offset) {
    if (typeof o === "string") {
      return this.__string(offset);
    }
    return this.__union(o, offset);
  }
  /**
   * Retrieve the relative offset stored at "offset"
   */
  __indirect(offset) {
    return offset + this.readInt32(offset);
  }
  /**
   * Get the start of data of a vector whose offset is stored at "offset" in this object.
   */
  __vector(offset) {
    return offset + this.readInt32(offset) + SIZEOF_INT$1;
  }
  /**
   * Get the length of a vector whose offset is stored at "offset" in this object.
   */
  __vector_len(offset) {
    return this.readInt32(offset + this.readInt32(offset));
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
  addOffset(offset) {
    this.prep(SIZEOF_INT$1, 0);
    this.writeInt32(this.offset() - offset + SIZEOF_INT$1);
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
    const offset = this.createString(s);
    this.string_maps.set(s, offset);
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt8(this.bb_pos + offset) : CompressionType.LZ4_FRAME;
  }
  /**
   * Indicates the way the record batch body was compressed
   */
  method() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.readInt8(this.bb_pos + offset) : BodyCompressionMethod.BUFFER;
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
    const offset = builder2.endObject();
    return offset;
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
  static createBuffer(builder2, offset, length) {
    builder2.prep(8, 16);
    builder2.writeInt64(BigInt(length !== null && length !== void 0 ? length : 0));
    builder2.writeInt64(BigInt(offset !== null && offset !== void 0 ? offset : 0));
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
  static createFieldNode(builder2, length, null_count) {
    builder2.prep(8, 16);
    builder2.writeInt64(BigInt(null_count !== null && null_count !== void 0 ? null_count : 0));
    builder2.writeInt64(BigInt(length !== null && length !== void 0 ? length : 0));
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt64(this.bb_pos + offset) : BigInt("0");
  }
  /**
   * Nodes correspond to the pre-ordered flattened logical schema
   */
  nodes(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? (obj || new FieldNode$1()).__init(this.bb.__vector(this.bb_pos + offset) + index * 16, this.bb) : null;
  }
  nodesLength() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
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
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? (obj || new Buffer$1()).__init(this.bb.__vector(this.bb_pos + offset) + index * 16, this.bb) : null;
  }
  buffersLength() {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  /**
   * Optional compression of the message body
   */
  compression(obj) {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? (obj || new BodyCompression$1()).__init(this.bb.__indirect(this.bb_pos + offset), this.bb) : null;
  }
  static startRecordBatch(builder2) {
    builder2.startObject(4);
  }
  static addLength(builder2, length) {
    builder2.addFieldInt64(0, length, BigInt("0"));
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt64(this.bb_pos + offset) : BigInt("0");
  }
  data(obj) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? (obj || new RecordBatch$2()).__init(this.bb.__indirect(this.bb_pos + offset), this.bb) : null;
  }
  /**
   * If isDelta is true the values in the dictionary are to be appended to a
   * dictionary with the indicated id. If isDelta is false this dictionary
   * should replace the existing dictionary.
   */
  isDelta() {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? !!this.bb.readInt8(this.bb_pos + offset) : false;
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
    const offset = builder2.endObject();
    return offset;
  }
};
var Endianness;
(function(Endianness2) {
  Endianness2[Endianness2["Little"] = 0] = "Little";
  Endianness2[Endianness2["Big"] = 1] = "Big";
})(Endianness || (Endianness = {}));
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt32(this.bb_pos + offset) : 0;
  }
  isSigned() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? !!this.bb.readInt8(this.bb_pos + offset) : false;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt64(this.bb_pos + offset) : BigInt("0");
  }
  /**
   * The dictionary indices are constrained to be non-negative integers. If
   * this field is null, the indices must be signed int32. To maximize
   * cross-language compatibility and performance, implementations are
   * recommended to prefer signed integer types over unsigned integer types
   * and to avoid uint64 indices unless they are required by an application.
   */
  indexType(obj) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? (obj || new Int()).__init(this.bb.__indirect(this.bb_pos + offset), this.bb) : null;
  }
  /**
   * By default, dictionaries are not ordered, or the order does not have
   * semantic meaning. In some statistical, applications, dictionary-encoding
   * is used to represent ordered categorical data, and we provide a way to
   * preserve that metadata here
   */
  isOrdered() {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? !!this.bb.readInt8(this.bb_pos + offset) : false;
  }
  dictionaryKind() {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : DictionaryKind.DenseArray;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.__string(this.bb_pos + offset, optionalEncoding) : null;
  }
  value(optionalEncoding) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.__string(this.bb_pos + offset, optionalEncoding) : null;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : DateUnit.MILLISECOND;
  }
  static startDate(builder2) {
    builder2.startObject(1);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, DateUnit.MILLISECOND);
  }
  static endDate(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt32(this.bb_pos + offset) : 0;
  }
  /**
   * Number of digits after the decimal point "."
   */
  scale() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.readInt32(this.bb_pos + offset) : 0;
  }
  /**
   * Number of bits per value. The only accepted widths are 128 and 256.
   * We use bitWidth for consistency with Int::bitWidth.
   */
  bitWidth() {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? this.bb.readInt32(this.bb_pos + offset) : 128;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : TimeUnit.MILLISECOND;
  }
  static startDuration(builder2) {
    builder2.startObject(1);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, TimeUnit.MILLISECOND);
  }
  static endDuration(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt32(this.bb_pos + offset) : 0;
  }
  static startFixedSizeBinary(builder2) {
    builder2.startObject(1);
  }
  static addByteWidth(builder2, byteWidth) {
    builder2.addFieldInt32(0, byteWidth, 0);
  }
  static endFixedSizeBinary(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt32(this.bb_pos + offset) : 0;
  }
  static startFixedSizeList(builder2) {
    builder2.startObject(1);
  }
  static addListSize(builder2, listSize) {
    builder2.addFieldInt32(0, listSize, 0);
  }
  static endFixedSizeList(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : Precision.HALF;
  }
  static startFloatingPoint(builder2) {
    builder2.startObject(1);
  }
  static addPrecision(builder2, precision) {
    builder2.addFieldInt16(0, precision, Precision.HALF);
  }
  static endFloatingPoint(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : IntervalUnit.YEAR_MONTH;
  }
  static startInterval(builder2) {
    builder2.startObject(1);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, IntervalUnit.YEAR_MONTH);
  }
  static endInterval(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? !!this.bb.readInt8(this.bb_pos + offset) : false;
  }
  static startMap(builder2) {
    builder2.startObject(1);
  }
  static addKeysSorted(builder2, keysSorted) {
    builder2.addFieldInt8(0, +keysSorted, 0);
  }
  static endMap(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : TimeUnit.MILLISECOND;
  }
  bitWidth() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.readInt32(this.bb_pos + offset) : 32;
  }
  static startTime(builder2) {
    builder2.startObject(2);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, TimeUnit.MILLISECOND);
  }
  static addBitWidth(builder2, bitWidth) {
    builder2.addFieldInt32(1, bitWidth, 32);
  }
  static endTime(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : TimeUnit.SECOND;
  }
  timezone(optionalEncoding) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.__string(this.bb_pos + offset, optionalEncoding) : null;
  }
  static startTimestamp(builder2) {
    builder2.startObject(2);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, TimeUnit.SECOND);
  }
  static addTimezone(builder2, timezoneOffset) {
    builder2.addFieldOffset(1, timezoneOffset, 0);
  }
  static endTimestamp(builder2) {
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : UnionMode.Sparse;
  }
  typeIds(index) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.readInt32(this.bb.__vector(this.bb_pos + offset) + index * 4) : 0;
  }
  typeIdsLength() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  typeIdsArray() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? new Int32Array(this.bb.bytes().buffer, this.bb.bytes().byteOffset + this.bb.__vector(this.bb_pos + offset), this.bb.__vector_len(this.bb_pos + offset)) : null;
  }
  static startUnion(builder2) {
    builder2.startObject(2);
  }
  static addMode(builder2, mode) {
    builder2.addFieldInt16(0, mode, UnionMode.Sparse);
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = builder2.endObject();
    return offset;
  }
  static createUtf8(builder2) {
    Utf8.startUtf8(builder2);
    return Utf8.endUtf8(builder2);
  }
};
var Type$1;
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
})(Type$1 || (Type$1 = {}));
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.__string(this.bb_pos + offset, optionalEncoding) : null;
  }
  /**
   * Whether or not this field can contain nulls. Should be true in general.
   */
  nullable() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? !!this.bb.readInt8(this.bb_pos + offset) : false;
  }
  typeType() {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? this.bb.readUint8(this.bb_pos + offset) : Type$1.NONE;
  }
  /**
   * This is the type of the decoded value if the field is dictionary encoded.
   */
  type(obj) {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? this.bb.__union(obj, this.bb_pos + offset) : null;
  }
  /**
   * Present only if the field is dictionary encoded.
   */
  dictionary(obj) {
    const offset = this.bb.__offset(this.bb_pos, 12);
    return offset ? (obj || new DictionaryEncoding()).__init(this.bb.__indirect(this.bb_pos + offset), this.bb) : null;
  }
  /**
   * children apply only to nested data types like Struct, List and Union. For
   * primitive types children will have length 0.
   */
  children(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 14);
    return offset ? (obj || new Field()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset) + index * 4), this.bb) : null;
  }
  childrenLength() {
    const offset = this.bb.__offset(this.bb_pos, 14);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  /**
   * User-defined metadata
   */
  customMetadata(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 16);
    return offset ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset = this.bb.__offset(this.bb_pos, 16);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
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
    builder2.addFieldInt8(2, typeType, Type$1.NONE);
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
    const offset = builder2.endObject();
    return offset;
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : Endianness.Little;
  }
  fields(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? (obj || new Field$1()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset) + index * 4), this.bb) : null;
  }
  fieldsLength() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  customMetadata(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  /**
   * Features used in the stream/file.
   */
  features(index) {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? this.bb.readInt64(this.bb.__vector(this.bb_pos + offset) + index * 8) : BigInt(0);
  }
  featuresLength() {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  static startSchema(builder2) {
    builder2.startObject(4);
  }
  static addEndianness(builder2, endianness) {
    builder2.addFieldInt16(0, endianness, Endianness.Little);
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
    const offset = builder2.endObject();
    return offset;
  }
  static finishSchemaBuffer(builder2, offset) {
    builder2.finish(offset);
  }
  static finishSizePrefixedSchemaBuffer(builder2, offset) {
    builder2.finish(offset, void 0, true);
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
var MessageHeader;
(function(MessageHeader2) {
  MessageHeader2[MessageHeader2["NONE"] = 0] = "NONE";
  MessageHeader2[MessageHeader2["Schema"] = 1] = "Schema";
  MessageHeader2[MessageHeader2["DictionaryBatch"] = 2] = "DictionaryBatch";
  MessageHeader2[MessageHeader2["RecordBatch"] = 3] = "RecordBatch";
  MessageHeader2[MessageHeader2["Tensor"] = 4] = "Tensor";
  MessageHeader2[MessageHeader2["SparseTensor"] = 5] = "SparseTensor";
})(MessageHeader || (MessageHeader = {}));
var Type;
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
})(Type || (Type = {}));
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
    const sign = negative && integerPart === 0 ? "-" : "";
    return +`${sign}${integerPart}.${fractionPart}`;
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
  let array = new Uint16Array(a.buffer, a.byteOffset, a.byteLength / 2);
  const highOrderWord = new Int16Array([array.at(-1)])[0];
  if (highOrderWord >= 0) {
    return unsignedBigNumToString(a);
  }
  array = array.slice();
  let carry = 1;
  for (let i = 0; i < array.length; i++) {
    const elem = array[i];
    const updated = ~elem + carry;
    array[i] = updated;
    carry &= elem === 0 ? 1 : 0;
  }
  const negated = unsignedBigNumToString(array);
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
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Null;
  }
  /** @nocollapse */
  static isInt(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Int;
  }
  /** @nocollapse */
  static isFloat(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Float;
  }
  /** @nocollapse */
  static isBinary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Binary;
  }
  /** @nocollapse */
  static isLargeBinary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.LargeBinary;
  }
  /** @nocollapse */
  static isUtf8(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Utf8;
  }
  /** @nocollapse */
  static isLargeUtf8(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.LargeUtf8;
  }
  /** @nocollapse */
  static isBool(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Bool;
  }
  /** @nocollapse */
  static isDecimal(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Decimal;
  }
  /** @nocollapse */
  static isDate(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Date;
  }
  /** @nocollapse */
  static isTime(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Time;
  }
  /** @nocollapse */
  static isTimestamp(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Timestamp;
  }
  /** @nocollapse */
  static isInterval(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Interval;
  }
  /** @nocollapse */
  static isDuration(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Duration;
  }
  /** @nocollapse */
  static isList(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.List;
  }
  /** @nocollapse */
  static isStruct(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Struct;
  }
  /** @nocollapse */
  static isUnion(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Union;
  }
  /** @nocollapse */
  static isFixedSizeBinary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.FixedSizeBinary;
  }
  /** @nocollapse */
  static isFixedSizeList(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.FixedSizeList;
  }
  /** @nocollapse */
  static isMap(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Map;
  }
  /** @nocollapse */
  static isDictionary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type.Dictionary;
  }
  /** @nocollapse */
  static isDenseUnion(x) {
    return DataType.isUnion(x) && x.mode === UnionMode.Dense;
  }
  /** @nocollapse */
  static isSparseUnion(x) {
    return DataType.isUnion(x) && x.mode === UnionMode.Sparse;
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
    super(Type.Null);
  }
  toString() {
    return `Null`;
  }
}
_b = Symbol.toStringTag;
Null2[_b] = ((proto) => proto[Symbol.toStringTag] = "Null")(Null2.prototype);
class Int_ extends DataType {
  constructor(isSigned, bitWidth) {
    super(Type.Int);
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
    super(Type.Float);
    this.precision = precision;
  }
  get ArrayType() {
    switch (this.precision) {
      case Precision.HALF:
        return Uint16Array;
      case Precision.SINGLE:
        return Float32Array;
      case Precision.DOUBLE:
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
    super(Type.Binary);
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
    super(Type.LargeBinary);
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
    super(Type.Utf8);
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
    super(Type.LargeUtf8);
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
    super(Type.Bool);
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
    super(Type.Decimal);
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
    super(Type.Date);
    this.unit = unit;
  }
  toString() {
    return `Date${(this.unit + 1) * 32}<${DateUnit[this.unit]}>`;
  }
  get ArrayType() {
    return this.unit === DateUnit.DAY ? Int32Array : BigInt64Array;
  }
}
_l = Symbol.toStringTag;
Date_[_l] = ((proto) => {
  proto.unit = null;
  return proto[Symbol.toStringTag] = "Date";
})(Date_.prototype);
class Time_ extends DataType {
  constructor(unit, bitWidth) {
    super(Type.Time);
    this.unit = unit;
    this.bitWidth = bitWidth;
  }
  toString() {
    return `Time${this.bitWidth}<${TimeUnit[this.unit]}>`;
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
    super(Type.Timestamp);
    this.unit = unit;
    this.timezone = timezone;
  }
  toString() {
    return `Timestamp<${TimeUnit[this.unit]}${this.timezone ? `, ${this.timezone}` : ``}>`;
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
    super(Type.Interval);
    this.unit = unit;
  }
  toString() {
    return `Interval<${IntervalUnit[this.unit]}>`;
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
    super(Type.Duration);
    this.unit = unit;
  }
  toString() {
    return `Duration<${TimeUnit[this.unit]}>`;
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
    super(Type.List);
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
    super(Type.Struct);
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
    super(Type.Union);
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
    super(Type.FixedSizeBinary);
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
    super(Type.FixedSizeList);
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
    super(Type.Map);
    this.children = [entries2];
    this.keysSorted = keysSorted;
    if (entries2) {
      entries2["name"] = "entries";
      if ((_y = entries2 === null || entries2 === void 0 ? void 0 : entries2.type) === null || _y === void 0 ? void 0 : _y.children) {
        const key = (_z = entries2 === null || entries2 === void 0 ? void 0 : entries2.type) === null || _z === void 0 ? void 0 : _z.children[0];
        if (key) {
          key["name"] = "key";
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
class Dictionary extends DataType {
  constructor(dictionary2, indices, id, isOrdered) {
    super(Type.Dictionary);
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
}
_x = Symbol.toStringTag;
Dictionary[_x] = ((proto) => {
  proto.id = null;
  proto.indices = null;
  proto.isOrdered = null;
  proto.dictionary = null;
  return proto[Symbol.toStringTag] = "Dictionary";
})(Dictionary.prototype);
function strideForType(type) {
  const t = type;
  switch (type.typeId) {
    case Type.Decimal:
      return type.bitWidth / 32;
    case Type.Interval: {
      if (t.unit === IntervalUnit.MONTH_DAY_NANO) {
        return 4;
      }
      return 1 + t.unit;
    }
    // case Type.Int: return 1 + +((t as Int_).bitWidth > 32);
    // case Type.Time: return 1 + +((t as Time_).bitWidth > 32);
    case Type.FixedSizeList:
      return t.listSize;
    case Type.FixedSizeBinary:
      return t.byteWidth;
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
  if (typeof node === "string" && node in Type) {
    return getVisitFnByTypeId(visitor, Type[node], throwIfNotFound);
  }
  if (node && node instanceof DataType) {
    return getVisitFnByTypeId(visitor, inferDType(node), throwIfNotFound);
  }
  if ((node === null || node === void 0 ? void 0 : node.type) && node.type instanceof DataType) {
    return getVisitFnByTypeId(visitor, inferDType(node.type), throwIfNotFound);
  }
  return getVisitFnByTypeId(visitor, Type.NONE, throwIfNotFound);
}
function getVisitFnByTypeId(visitor, dtype, throwIfNotFound = true) {
  let fn = null;
  switch (dtype) {
    case Type.Null:
      fn = visitor.visitNull;
      break;
    case Type.Bool:
      fn = visitor.visitBool;
      break;
    case Type.Int:
      fn = visitor.visitInt;
      break;
    case Type.Int8:
      fn = visitor.visitInt8 || visitor.visitInt;
      break;
    case Type.Int16:
      fn = visitor.visitInt16 || visitor.visitInt;
      break;
    case Type.Int32:
      fn = visitor.visitInt32 || visitor.visitInt;
      break;
    case Type.Int64:
      fn = visitor.visitInt64 || visitor.visitInt;
      break;
    case Type.Uint8:
      fn = visitor.visitUint8 || visitor.visitInt;
      break;
    case Type.Uint16:
      fn = visitor.visitUint16 || visitor.visitInt;
      break;
    case Type.Uint32:
      fn = visitor.visitUint32 || visitor.visitInt;
      break;
    case Type.Uint64:
      fn = visitor.visitUint64 || visitor.visitInt;
      break;
    case Type.Float:
      fn = visitor.visitFloat;
      break;
    case Type.Float16:
      fn = visitor.visitFloat16 || visitor.visitFloat;
      break;
    case Type.Float32:
      fn = visitor.visitFloat32 || visitor.visitFloat;
      break;
    case Type.Float64:
      fn = visitor.visitFloat64 || visitor.visitFloat;
      break;
    case Type.Utf8:
      fn = visitor.visitUtf8;
      break;
    case Type.LargeUtf8:
      fn = visitor.visitLargeUtf8;
      break;
    case Type.Binary:
      fn = visitor.visitBinary;
      break;
    case Type.LargeBinary:
      fn = visitor.visitLargeBinary;
      break;
    case Type.FixedSizeBinary:
      fn = visitor.visitFixedSizeBinary;
      break;
    case Type.Date:
      fn = visitor.visitDate;
      break;
    case Type.DateDay:
      fn = visitor.visitDateDay || visitor.visitDate;
      break;
    case Type.DateMillisecond:
      fn = visitor.visitDateMillisecond || visitor.visitDate;
      break;
    case Type.Timestamp:
      fn = visitor.visitTimestamp;
      break;
    case Type.TimestampSecond:
      fn = visitor.visitTimestampSecond || visitor.visitTimestamp;
      break;
    case Type.TimestampMillisecond:
      fn = visitor.visitTimestampMillisecond || visitor.visitTimestamp;
      break;
    case Type.TimestampMicrosecond:
      fn = visitor.visitTimestampMicrosecond || visitor.visitTimestamp;
      break;
    case Type.TimestampNanosecond:
      fn = visitor.visitTimestampNanosecond || visitor.visitTimestamp;
      break;
    case Type.Time:
      fn = visitor.visitTime;
      break;
    case Type.TimeSecond:
      fn = visitor.visitTimeSecond || visitor.visitTime;
      break;
    case Type.TimeMillisecond:
      fn = visitor.visitTimeMillisecond || visitor.visitTime;
      break;
    case Type.TimeMicrosecond:
      fn = visitor.visitTimeMicrosecond || visitor.visitTime;
      break;
    case Type.TimeNanosecond:
      fn = visitor.visitTimeNanosecond || visitor.visitTime;
      break;
    case Type.Decimal:
      fn = visitor.visitDecimal;
      break;
    case Type.List:
      fn = visitor.visitList;
      break;
    case Type.Struct:
      fn = visitor.visitStruct;
      break;
    case Type.Union:
      fn = visitor.visitUnion;
      break;
    case Type.DenseUnion:
      fn = visitor.visitDenseUnion || visitor.visitUnion;
      break;
    case Type.SparseUnion:
      fn = visitor.visitSparseUnion || visitor.visitUnion;
      break;
    case Type.Dictionary:
      fn = visitor.visitDictionary;
      break;
    case Type.Interval:
      fn = visitor.visitInterval;
      break;
    case Type.IntervalDayTime:
      fn = visitor.visitIntervalDayTime || visitor.visitInterval;
      break;
    case Type.IntervalYearMonth:
      fn = visitor.visitIntervalYearMonth || visitor.visitInterval;
      break;
    case Type.IntervalMonthDayNano:
      fn = visitor.visitIntervalMonthDayNano || visitor.visitInterval;
      break;
    case Type.Duration:
      fn = visitor.visitDuration;
      break;
    case Type.DurationSecond:
      fn = visitor.visitDurationSecond || visitor.visitDuration;
      break;
    case Type.DurationMillisecond:
      fn = visitor.visitDurationMillisecond || visitor.visitDuration;
      break;
    case Type.DurationMicrosecond:
      fn = visitor.visitDurationMicrosecond || visitor.visitDuration;
      break;
    case Type.DurationNanosecond:
      fn = visitor.visitDurationNanosecond || visitor.visitDuration;
      break;
    case Type.FixedSizeList:
      fn = visitor.visitFixedSizeList;
      break;
    case Type.Map:
      fn = visitor.visitMap;
      break;
  }
  if (typeof fn === "function")
    return fn;
  if (!throwIfNotFound)
    return () => null;
  throw new Error(`Unrecognized type '${Type[dtype]}'`);
}
function inferDType(type) {
  switch (type.typeId) {
    case Type.Null:
      return Type.Null;
    case Type.Int: {
      const { bitWidth, isSigned } = type;
      switch (bitWidth) {
        case 8:
          return isSigned ? Type.Int8 : Type.Uint8;
        case 16:
          return isSigned ? Type.Int16 : Type.Uint16;
        case 32:
          return isSigned ? Type.Int32 : Type.Uint32;
        case 64:
          return isSigned ? Type.Int64 : Type.Uint64;
      }
      return Type.Int;
    }
    case Type.Float:
      switch (type.precision) {
        case Precision.HALF:
          return Type.Float16;
        case Precision.SINGLE:
          return Type.Float32;
        case Precision.DOUBLE:
          return Type.Float64;
      }
      return Type.Float;
    case Type.Binary:
      return Type.Binary;
    case Type.LargeBinary:
      return Type.LargeBinary;
    case Type.Utf8:
      return Type.Utf8;
    case Type.LargeUtf8:
      return Type.LargeUtf8;
    case Type.Bool:
      return Type.Bool;
    case Type.Decimal:
      return Type.Decimal;
    case Type.Time:
      switch (type.unit) {
        case TimeUnit.SECOND:
          return Type.TimeSecond;
        case TimeUnit.MILLISECOND:
          return Type.TimeMillisecond;
        case TimeUnit.MICROSECOND:
          return Type.TimeMicrosecond;
        case TimeUnit.NANOSECOND:
          return Type.TimeNanosecond;
      }
      return Type.Time;
    case Type.Timestamp:
      switch (type.unit) {
        case TimeUnit.SECOND:
          return Type.TimestampSecond;
        case TimeUnit.MILLISECOND:
          return Type.TimestampMillisecond;
        case TimeUnit.MICROSECOND:
          return Type.TimestampMicrosecond;
        case TimeUnit.NANOSECOND:
          return Type.TimestampNanosecond;
      }
      return Type.Timestamp;
    case Type.Date:
      switch (type.unit) {
        case DateUnit.DAY:
          return Type.DateDay;
        case DateUnit.MILLISECOND:
          return Type.DateMillisecond;
      }
      return Type.Date;
    case Type.Interval:
      switch (type.unit) {
        case IntervalUnit.DAY_TIME:
          return Type.IntervalDayTime;
        case IntervalUnit.YEAR_MONTH:
          return Type.IntervalYearMonth;
        case IntervalUnit.MONTH_DAY_NANO:
          return Type.IntervalMonthDayNano;
      }
      return Type.Interval;
    case Type.Duration:
      switch (type.unit) {
        case TimeUnit.SECOND:
          return Type.DurationSecond;
        case TimeUnit.MILLISECOND:
          return Type.DurationMillisecond;
        case TimeUnit.MICROSECOND:
          return Type.DurationMicrosecond;
        case TimeUnit.NANOSECOND:
          return Type.DurationNanosecond;
      }
      return Type.Duration;
    case Type.Map:
      return Type.Map;
    case Type.List:
      return Type.List;
    case Type.Struct:
      return Type.Struct;
    case Type.Union:
      switch (type.mode) {
        case UnionMode.Dense:
          return Type.DenseUnion;
        case UnionMode.Sparse:
          return Type.SparseUnion;
      }
      return Type.Union;
    case Type.FixedSizeBinary:
      return Type.FixedSizeBinary;
    case Type.FixedSizeList:
      return Type.FixedSizeList;
    case Type.Dictionary:
      return Type.Dictionary;
  }
  throw new Error(`Unrecognized type '${Type[type.typeId]}'`);
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
const f64 = new Float64Array(1);
const u32 = new Uint32Array(f64.buffer);
function uint16ToFloat64(h) {
  const expo = (h & 31744) >> 10;
  const sigf = (h & 1023) / 1024;
  const sign = Math.pow(-1, (h & 32768) >> 15);
  switch (expo) {
    case 31:
      return sign * (sigf ? Number.NaN : 1 / 0);
    case 0:
      return sign * (sigf ? 6103515625e-14 * sigf : 0);
  }
  return sign * Math.pow(2, expo - 15) * (1 + sigf);
}
function float64ToUint16(d) {
  if (d !== d) {
    return 32256;
  }
  f64[0] = d;
  const sign = (u32[1] & 2147483648) >> 16 & 65535;
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
  return sign | expo | sigf & 65535;
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
const setBool = ({ offset, values: values2 }, index, val) => {
  const idx = offset + index;
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
    case Precision.HALF:
      return setFloat16(data2, index, value2);
    case Precision.SINGLE:
    case Precision.DOUBLE:
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
const setUtf8 = ({ values: values2, valueOffsets }, index, value2) => setVariableWidthBytes(values2, valueOffsets, index, encodeUtf8(value2));
const setDate = (data2, index, value2) => {
  data2.type.unit === DateUnit.DAY ? setDateDay(data2, index, value2) : setDateMillisecond(data2, index, value2);
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
    case TimeUnit.SECOND:
      return setTimestampSecond(data2, index, value2);
    case TimeUnit.MILLISECOND:
      return setTimestampMillisecond(data2, index, value2);
    case TimeUnit.MICROSECOND:
      return setTimestampMicrosecond(data2, index, value2);
    case TimeUnit.NANOSECOND:
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
    case TimeUnit.SECOND:
      return setTimeSecond(data2, index, value2);
    case TimeUnit.MILLISECOND:
      return setTimeMillisecond(data2, index, value2);
    case TimeUnit.MICROSECOND:
      return setTimeMicrosecond(data2, index, value2);
    case TimeUnit.NANOSECOND:
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
  data2.type.mode === UnionMode.Dense ? setDenseUnion(data2, index, value2) : setSparseUnion(data2, index, value2);
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
    case IntervalUnit.YEAR_MONTH:
      return setIntervalYearMonth(data2, index, value2);
    case IntervalUnit.DAY_TIME:
      return setIntervalDayTime(data2, index, value2);
    case IntervalUnit.MONTH_DAY_NANO:
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
    case TimeUnit.SECOND:
      return setDurationSecond(data2, index, value2);
    case TimeUnit.MILLISECOND:
      return setDurationMillisecond(data2, index, value2);
    case TimeUnit.MICROSECOND:
      return setDurationMicrosecond(data2, index, value2);
    case TimeUnit.NANOSECOND:
      return setDurationNanosecond(data2, index, value2);
  }
};
const setFixedSizeList = (data2, index, value2) => {
  const { stride } = data2;
  const child = data2.children[0];
  const set = instance$5.getVisitFn(child);
  if (Array.isArray(value2)) {
    for (let idx = -1, offset = index * stride; ++idx < stride; ) {
      set(child, offset + idx, value2[idx]);
    }
  } else {
    for (let idx = -1, offset = index * stride; ++idx < stride; ) {
      set(child, offset + idx, value2.get(idx));
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
    const keys = parent.type.children;
    const json = {};
    for (let j = -1, n = keys.length; ++j < n; ) {
      json[keys[j].name] = instance$4.visit(parent.children[j], i);
    }
    return json;
  }
  toString() {
    return `{${[...this].map(([key, val]) => `${valueToString(key)}: ${valueToString(val)}`).join(", ")}}`;
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
  has(row, key) {
    return row[kParent].type.children.some((f) => f.name === key);
  }
  getOwnPropertyDescriptor(row, key) {
    if (row[kParent].type.children.some((f) => f.name === key)) {
      return { writable: true, enumerable: true, configurable: true };
    }
    return;
  }
  get(row, key) {
    if (Reflect.has(row, key)) {
      return row[key];
    }
    const idx = row[kParent].type.children.findIndex((f) => f.name === key);
    if (idx !== -1) {
      const val = instance$4.visit(row[kParent].children[idx], row[kRowIndex]);
      Reflect.set(row, key, val);
      return val;
    }
  }
  set(row, key, val) {
    const idx = row[kParent].type.children.findIndex((f) => f.name === key);
    if (idx !== -1) {
      instance$5.visit(row[kParent].children[idx], row[kRowIndex], val);
      return Reflect.set(row, key, val);
    } else if (Reflect.has(row, key) || typeof key === "symbol") {
      return Reflect.set(row, key, val);
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
const getBool$1 = ({ offset, values: values2 }, index) => {
  const idx = offset + index;
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
  return bytes !== null ? decodeUtf8(bytes) : null;
};
const getInt = ({ values: values2 }, index) => values2[index];
const getFloat = ({ type, values: values2 }, index) => type.precision !== Precision.HALF ? values2[index] : uint16ToFloat64(values2[index]);
const getDate = (data2, index) => data2.type.unit === DateUnit.DAY ? getDateDay(data2, index) : getDateMillisecond(data2, index);
const getTimestampSecond = ({ values: values2 }, index) => 1e3 * bigIntToNumber(values2[index]);
const getTimestampMillisecond = ({ values: values2 }, index) => bigIntToNumber(values2[index]);
const getTimestampMicrosecond = ({ values: values2 }, index) => divideBigInts(values2[index], BigInt(1e3));
const getTimestampNanosecond = ({ values: values2 }, index) => divideBigInts(values2[index], BigInt(1e6));
const getTimestamp = (data2, index) => {
  switch (data2.type.unit) {
    case TimeUnit.SECOND:
      return getTimestampSecond(data2, index);
    case TimeUnit.MILLISECOND:
      return getTimestampMillisecond(data2, index);
    case TimeUnit.MICROSECOND:
      return getTimestampMicrosecond(data2, index);
    case TimeUnit.NANOSECOND:
      return getTimestampNanosecond(data2, index);
  }
};
const getTimeSecond = ({ values: values2 }, index) => values2[index];
const getTimeMillisecond = ({ values: values2 }, index) => values2[index];
const getTimeMicrosecond = ({ values: values2 }, index) => values2[index];
const getTimeNanosecond = ({ values: values2 }, index) => values2[index];
const getTime = (data2, index) => {
  switch (data2.type.unit) {
    case TimeUnit.SECOND:
      return getTimeSecond(data2, index);
    case TimeUnit.MILLISECOND:
      return getTimeMillisecond(data2, index);
    case TimeUnit.MICROSECOND:
      return getTimeMicrosecond(data2, index);
    case TimeUnit.NANOSECOND:
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
  return data2.type.mode === UnionMode.Dense ? getDenseUnion(data2, index) : getSparseUnion(data2, index);
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
const getInterval = (data2, index) => data2.type.unit === IntervalUnit.MONTH_DAY_NANO ? getIntervalMonthDayNano(data2, index) : data2.type.unit === IntervalUnit.DAY_TIME ? getIntervalDayTime(data2, index) : getIntervalYearMonth(data2, index);
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
    case TimeUnit.SECOND:
      return getDurationSecond(data2, index);
    case TimeUnit.MILLISECOND:
      return getDurationMillisecond(data2, index);
    case TimeUnit.MICROSECOND:
      return getDurationMicrosecond(data2, index);
    case TimeUnit.NANOSECOND:
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
    const keys = this[kKeys];
    const vals = this[kVals];
    const json = {};
    for (let i = -1, n = keys.length; ++i < n; ) {
      json[keys.get(i)] = instance$4.visit(vals, i);
    }
    return json;
  }
  toString() {
    return `{${[...this].map(([key, val]) => `${valueToString(key)}: ${valueToString(val)}`).join(", ")}}`;
  }
  [/* @__PURE__ */ Symbol.for("nodejs.util.inspect.custom")]() {
    return this.toString();
  }
}
class MapRowIterator {
  constructor(keys, vals) {
    this.keys = keys;
    this.vals = vals;
    this.keyIndex = 0;
    this.numKeys = keys.length;
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
  has(row, key) {
    return row[kKeysAsStrings].includes(key);
  }
  getOwnPropertyDescriptor(row, key) {
    const idx = row[kKeysAsStrings].indexOf(key);
    if (idx !== -1) {
      return { writable: true, enumerable: true, configurable: true };
    }
    return;
  }
  get(row, key) {
    if (Reflect.has(row, key)) {
      return row[key];
    }
    const idx = row[kKeysAsStrings].indexOf(key);
    if (idx !== -1) {
      const val = instance$4.visit(Reflect.get(row, kVals), idx);
      Reflect.set(row, key, val);
      return val;
    }
  }
  set(row, key, val) {
    const idx = row[kKeysAsStrings].indexOf(key);
    if (idx !== -1) {
      instance$5.visit(Reflect.get(row, kVals), idx, val);
      return Reflect.set(row, key, val);
    } else if (Reflect.has(row, key)) {
      return Reflect.set(row, key, val);
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
function clampRange(source, begin, end, then) {
  const { length: len = 0 } = source;
  let lhs = typeof begin !== "number" ? 0 : begin;
  let rhs = typeof end !== "number" ? len : end;
  lhs < 0 && (lhs = (lhs % len + len) % len);
  rhs < 0 && (rhs = (rhs % len + len) % len);
  rhs < lhs && (tmp = lhs, lhs = rhs, rhs = tmp);
  rhs > len && (rhs = len);
  return then ? then(source, lhs, rhs) : [lhs, rhs];
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
  const keys = Object.keys(lhs);
  if (!allowEmpty && keys.length === 0) {
    return () => false;
  }
  const comparators = [];
  for (let i = -1, n = keys.length; ++i < n; ) {
    comparators[i] = createElementComparator(lhs[keys[i]]);
  }
  return createSubElementsComparator(comparators, keys);
}
function createSubElementsComparator(comparators, keys) {
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
        return compareObject(comparators, rhs, keys || Object.keys(rhs));
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
function compareObject(comparators, obj, keys) {
  const lKeyItr = keys[Symbol.iterator]();
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
function truncateBitmap(offset, length, bitmap2) {
  const alignedSize = bitmap2.byteLength + 7 & -8;
  if (offset > 0 || bitmap2.byteLength < alignedSize) {
    const bytes = new Uint8Array(alignedSize);
    bytes.set(offset % 8 === 0 ? bitmap2.subarray(offset >> 3) : (
      // Otherwise iterate each bit from the offset and return a new one
      packBools(new BitIterator(bitmap2, offset, length, null, getBool)).subarray(0, alignedSize)
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
  constructor(bytes, begin, length, context, get2) {
    this.bytes = bytes;
    this.length = length;
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
  constructor(type, offset, length, nullCount, buffers, children = [], dictionary2) {
    this.type = type;
    this.children = children;
    this.dictionary = dictionary2;
    this.offset = Math.floor(Math.max(offset || 0, 0));
    this.length = Math.floor(Math.max(length || 0, 0));
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
      const indexInChild = union2.mode === UnionMode.Dense ? this.valueOffsets[index] : index;
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
      const indexInChild = union2.mode === UnionMode.Dense ? this.valueOffsets[index] : index;
      prev = child.getValid(indexInChild);
      child.setValid(indexInChild, value2);
    } else {
      let { nullBitmap } = this;
      const { offset, length } = this;
      const idx = offset + index;
      const mask = 1 << idx % 8;
      const byteOffset = idx >> 3;
      if (!nullBitmap || nullBitmap.byteLength <= byteOffset) {
        nullBitmap = new Uint8Array((offset + length + 63 & -64) >> 3).fill(255);
        if (this.nullCount > 0) {
          nullBitmap.set(truncateBitmap(offset, length, this.nullBitmap), 0);
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
  clone(type = this.type, offset = this.offset, length = this.length, nullCount = this._nullCount, buffers = this, children = this.children) {
    return new Data(type, offset, length, nullCount, buffers, children, this.dictionary);
  }
  slice(offset, length) {
    const { stride, typeId, children } = this;
    const nullCount = +(this._nullCount === 0) - 1;
    const childStride = typeId === 16 ? stride : 1;
    const buffers = this._sliceBuffers(offset, length, stride, typeId);
    return this.clone(
      this.type,
      this.offset + offset,
      length,
      nullCount,
      buffers,
      // Don't slice children if we have value offsets (the variable-width types)
      children.length === 0 || this.valueOffsets ? children : this._sliceChildren(children, childStride * offset, childStride * length)
    );
  }
  _changeLengthAndBackfillNullBitmap(newLength) {
    if (this.typeId === Type.Null) {
      return this.clone(this.type, 0, newLength, 0);
    }
    const { length, nullCount } = this;
    const bitmap2 = new Uint8Array((newLength + 63 & -64) >> 3).fill(255, 0, length >> 3);
    bitmap2[length >> 3] = (1 << length - (length & -8)) - 1;
    if (nullCount > 0) {
      bitmap2.set(truncateBitmap(this.offset, length, this.nullBitmap), 0);
    }
    const buffers = this.buffers;
    buffers[BufferType.VALIDITY] = bitmap2;
    return this.clone(this.type, 0, newLength, nullCount + (newLength - length), buffers);
  }
  _sliceBuffers(offset, length, stride, typeId) {
    let arr;
    const { buffers } = this;
    (arr = buffers[BufferType.TYPE]) && (buffers[BufferType.TYPE] = arr.subarray(offset, offset + length));
    (arr = buffers[BufferType.OFFSET]) && (buffers[BufferType.OFFSET] = arr.subarray(offset, offset + length + 1)) || // Otherwise if no offsets, slice the data buffer. Don't slice the data vector for Booleans, since the offset goes by bits not bytes
    (arr = buffers[BufferType.DATA]) && (buffers[BufferType.DATA] = typeId === 6 ? arr : arr.subarray(stride * offset, stride * (offset + length)));
    return buffers;
  }
  _sliceChildren(children, offset, length) {
    return children.map((child) => child.slice(offset, length));
  }
}
Data.prototype.children = Object.freeze([]);
class MakeDataVisitor extends Visitor {
  visit(props) {
    return this.getVisitFn(props["type"]).call(this, props);
  }
  visitNull(props) {
    const { ["type"]: type, ["offset"]: offset = 0, ["length"]: length = 0 } = props;
    return new Data(type, offset, length, length);
  }
  visitBool(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length >> 3, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitInt(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitFloat(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitUtf8(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitLargeUtf8(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toBigInt64Array(props["valueOffsets"]);
    const { ["length"]: length = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitBinary(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitLargeBinary(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toBigInt64Array(props["valueOffsets"]);
    const { ["length"]: length = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitFixedSizeBinary(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitDate(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitTimestamp(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitTime(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitDecimal(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitList(props) {
    const { ["type"]: type, ["offset"]: offset = 0, ["child"]: child } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [valueOffsets, void 0, nullBitmap], [child]);
  }
  visitStruct(props) {
    const { ["type"]: type, ["offset"]: offset = 0, ["children"]: children = [] } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const { length = children.reduce((len, { length: length2 }) => Math.max(len, length2), 0), nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, void 0, nullBitmap], children);
  }
  visitUnion(props) {
    const { ["type"]: type, ["offset"]: offset = 0, ["children"]: children = [] } = props;
    const typeIds = toArrayBufferView(type.ArrayType, props["typeIds"]);
    const { ["length"]: length = typeIds.length, ["nullCount"]: nullCount = -1 } = props;
    if (DataType.isSparseUnion(type)) {
      return new Data(type, offset, length, nullCount, [void 0, void 0, void 0, typeIds], children);
    }
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    return new Data(type, offset, length, nullCount, [valueOffsets, void 0, void 0, typeIds], children);
  }
  visitDictionary(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.indices.ArrayType, props["data"]);
    const { ["dictionary"]: dictionary2 = new Vector([new MakeDataVisitor().visit({ type: type.dictionary })]) } = props;
    const { ["length"]: length = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap], [], dictionary2);
  }
  visitInterval(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitDuration(props) {
    const { ["type"]: type, ["offset"]: offset = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, data2, nullBitmap]);
  }
  visitFixedSizeList(props) {
    const { ["type"]: type, ["offset"]: offset = 0, ["child"]: child = new MakeDataVisitor().visit({ type: type.valueType }) } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const { ["length"]: length = child.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [void 0, void 0, nullBitmap], [child]);
  }
  visitMap(props) {
    const { ["type"]: type, ["offset"]: offset = 0, ["child"]: child = new MakeDataVisitor().visit({ type: type.childType }) } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset, length, nullCount, [valueOffsets, void 0, nullBitmap], [child]);
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
    const offset = offsets[i];
    const { length } = chunk;
    if (offset >= end) {
      break;
    }
    if (begin >= offset + length) {
      continue;
    }
    if (offset >= begin && offset + length <= end) {
      slices.push(chunk);
      continue;
    }
    const from2 = Math.max(0, begin - offset);
    const to = Math.min(end - offset, length);
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
  return function(element, offset) {
    _1 = element;
    const data2 = this.data;
    const result2 = typeof offset !== "number" ? chunkedIndexOf(data2, 0, 0) : binarySearch(data2, this._offsets, offset, chunkedIndexOf);
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
      case Type.Union:
        break;
      // Dictionaries do have a nullBitmap, but their dictionary could also have null elements.
      case Type.Dictionary:
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
  (DataType.isInt(type) && type.bitWidth !== 64 || DataType.isTime(type) && type.bitWidth !== 64 || DataType.isFloat(type) && type.precision !== Precision.HALF)) {
    return new ChunkedIterator(vector.data.length, (chunkIndex) => {
      const data2 = vector.data[chunkIndex];
      return data2.values.subarray(0, data2.length)[Symbol.iterator]();
    });
  }
  let offset = 0;
  return new ChunkedIterator(vector.data.length, (chunkIndex) => {
    const data2 = vector.data[chunkIndex];
    const length = data2.length;
    const inner = vector.slice(offset, offset + length);
    offset += length;
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
    return `${Type[this.type.typeId]}Vector`;
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
  indexOf(element, offset) {
    return -1;
  }
  includes(element, offset) {
    return this.indexOf(element, offset) > -1;
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
    const { type, data: data2, length, stride, ArrayType } = this;
    switch (type.typeId) {
      case Type.Int:
      case Type.Float:
      case Type.Decimal:
      case Type.Time:
      case Type.Timestamp:
        switch (data2.length) {
          case 0:
            return new ArrayType();
          case 1:
            return data2[0].values.subarray(0, length * stride);
          default:
            return data2.reduce((memo, { values: values2, length: chunk_length }) => {
              memo.array.set(values2.subarray(0, chunk_length * stride), memo.offset);
              memo.offset += chunk_length * stride;
              return memo;
            }, { array: new ArrayType(length * stride), offset: 0 }).array;
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
  getChild(name) {
    var _b2;
    return this.getChildAt((_b2 = this.type.children) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name));
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
  const typeIds = Object.keys(Type).map((T) => Type[T]).filter((T) => typeof T === "number" && T !== Type.NONE);
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
  static createBlock(builder2, offset, metaDataLength, bodyLength) {
    builder2.prep(8, 24);
    builder2.writeInt64(BigInt(bodyLength !== null && bodyLength !== void 0 ? bodyLength : 0));
    builder2.pad(4);
    builder2.writeInt32(metaDataLength);
    builder2.writeInt64(BigInt(offset !== null && offset !== void 0 ? offset : 0));
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : MetadataVersion.V1;
  }
  schema(obj) {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? (obj || new Schema$1()).__init(this.bb.__indirect(this.bb_pos + offset), this.bb) : null;
  }
  dictionaries(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? (obj || new Block()).__init(this.bb.__vector(this.bb_pos + offset) + index * 24, this.bb) : null;
  }
  dictionariesLength() {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  recordBatches(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? (obj || new Block()).__init(this.bb.__vector(this.bb_pos + offset) + index * 24, this.bb) : null;
  }
  recordBatchesLength() {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  /**
   * User-defined metadata
   */
  customMetadata(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 12);
    return offset ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset = this.bb.__offset(this.bb_pos, 12);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  static startFooter(builder2) {
    builder2.startObject(5);
  }
  static addVersion(builder2, version) {
    builder2.addFieldInt16(0, version, MetadataVersion.V1);
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
    const offset = builder2.endObject();
    return offset;
  }
  static finishFooterBuffer(builder2, offset) {
    builder2.finish(offset);
  }
  static finishSizePrefixedFooterBuffer(builder2, offset) {
    builder2.finish(offset, void 0, true);
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
    let [name, type, nullable, metadata] = args;
    if (args[0] && typeof args[0] === "object") {
      ({ name } = args[0]);
      type === void 0 && (type = args[0].type);
      nullable === void 0 && (nullable = args[0].nullable);
      metadata === void 0 && (metadata = args[0].metadata);
    }
    return new Field2(`${name}`, type, nullable, metadata);
  }
  constructor(name, type, nullable = false, metadata) {
    this.name = name;
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
    let [name, type, nullable, metadata] = args;
    !args[0] || typeof args[0] !== "object" ? [name = this.name, type = this.type, nullable = this.nullable, metadata = this.metadata] = args : { name = this.name, type = this.type, nullable = this.nullable, metadata = this.metadata } = args[0];
    return Field2.new(name, type, nullable, metadata);
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
  static decode(buf) {
    buf = new ByteBuffer$1(toUint8Array(buf));
    const footer = Footer.getRootAsFooter(buf);
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
  constructor(schema, version = MetadataVersion.V5, recordBatches, dictionaryBatches) {
    this.schema = schema;
    this.version = version;
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
    const offset = BigInt(fileBlock.offset);
    const bodyLength = BigInt(fileBlock.bodyLength);
    return Block.createBlock(b, offset, metaDataLength, bodyLength);
  }
  constructor(metaDataLength, bodyLength, offset) {
    this.metaDataLength = metaDataLength;
    this.offset = bigIntToNumber(offset);
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
    const offset = this.bb.__offset(this.bb_pos, 4);
    return offset ? this.bb.readInt16(this.bb_pos + offset) : MetadataVersion.V1;
  }
  headerType() {
    const offset = this.bb.__offset(this.bb_pos, 6);
    return offset ? this.bb.readUint8(this.bb_pos + offset) : MessageHeader.NONE;
  }
  header(obj) {
    const offset = this.bb.__offset(this.bb_pos, 8);
    return offset ? this.bb.__union(obj, this.bb_pos + offset) : null;
  }
  bodyLength() {
    const offset = this.bb.__offset(this.bb_pos, 10);
    return offset ? this.bb.readInt64(this.bb_pos + offset) : BigInt("0");
  }
  customMetadata(index, obj) {
    const offset = this.bb.__offset(this.bb_pos, 12);
    return offset ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset = this.bb.__offset(this.bb_pos, 12);
    return offset ? this.bb.__vector_len(this.bb_pos + offset) : 0;
  }
  static startMessage(builder2) {
    builder2.startObject(5);
  }
  static addVersion(builder2, version) {
    builder2.addFieldInt16(0, version, MetadataVersion.V1);
  }
  static addHeaderType(builder2, headerType) {
    builder2.addFieldInt8(1, headerType, MessageHeader.NONE);
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
    const offset = builder2.endObject();
    return offset;
  }
  static finishMessageBuffer(builder2, offset) {
    builder2.finish(offset);
  }
  static finishSizePrefixedMessageBuffer(builder2, offset) {
    builder2.finish(offset, void 0, true);
  }
  static createMessage(builder2, version, headerType, headerOffset, bodyLength, customMetadataOffset) {
    Message.startMessage(builder2);
    Message.addVersion(builder2, version);
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
  let keys;
  let field2;
  let dictMeta;
  let type;
  let dictType;
  if (!dictionaries || !(dictMeta = _field["dictionary"])) {
    type = typeFromJSON(_field, fieldChildrenFromJSON(_field, dictionaries));
    field2 = new Field2(_field["name"], type, _field["nullable"], customMetadataFromJSON(_field["metadata"]));
  } else if (!dictionaries.has(id = dictMeta["id"])) {
    keys = (keys = dictMeta["indexType"]) ? indexTypeFromJSON(keys) : new Int32();
    dictionaries.set(id, type = typeFromJSON(_field, fieldChildrenFromJSON(_field, dictionaries)));
    dictType = new Dictionary(type, keys, id, dictMeta["isOrdered"]);
    field2 = new Field2(_field["name"], dictType, _field["nullable"], customMetadataFromJSON(_field["metadata"]));
  } else {
    keys = (keys = dictMeta["indexType"]) ? indexTypeFromJSON(keys) : new Int32();
    dictType = new Dictionary(dictionaries.get(id), keys, id, dictMeta["isOrdered"]);
    field2 = new Field2(_field["name"], dictType, _field["nullable"], customMetadataFromJSON(_field["metadata"]));
  }
  return field2 || null;
}
function customMetadataFromJSON(metadata = []) {
  return new Map(metadata.map(({ key, value: value2 }) => [key, value2]));
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
      const t = f["type"];
      return new Int_(t["isSigned"], t["bitWidth"]);
    }
    case "floatingpoint": {
      const t = f["type"];
      return new Float(Precision[t["precision"]]);
    }
    case "decimal": {
      const t = f["type"];
      return new Decimal2(t["scale"], t["precision"], t["bitWidth"]);
    }
    case "date": {
      const t = f["type"];
      return new Date_(DateUnit[t["unit"]]);
    }
    case "time": {
      const t = f["type"];
      return new Time_(TimeUnit[t["unit"]], t["bitWidth"]);
    }
    case "timestamp": {
      const t = f["type"];
      return new Timestamp_(TimeUnit[t["unit"]], t["timezone"]);
    }
    case "interval": {
      const t = f["type"];
      return new Interval_(IntervalUnit[t["unit"]]);
    }
    case "duration": {
      const t = f["type"];
      return new Duration2(TimeUnit[t["unit"]]);
    }
    case "union": {
      const t = f["type"];
      const [m, ...ms] = (t["mode"] + "").toLowerCase();
      const mode = m.toUpperCase() + ms.join("");
      return new Union_(UnionMode[mode], t["typeIds"] || [], children || []);
    }
    case "fixedsizebinary": {
      const t = f["type"];
      return new FixedSizeBinary2(t["byteWidth"]);
    }
    case "fixedsizelist": {
      const t = f["type"];
      return new FixedSizeList2(t["listSize"], (children || [])[0]);
    }
    case "map": {
      const t = f["type"];
      return new Map_((children || [])[0], t["keysSorted"]);
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
  static decode(buf) {
    buf = new ByteBuffer2(toUint8Array(buf));
    const _message = Message$1.getRootAsMessage(buf);
    const bodyLength = _message.bodyLength();
    const version = _message.version();
    const headerType = _message.headerType();
    const message = new Message2(bodyLength, version, headerType);
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
      return new Message2(0, MetadataVersion.V5, MessageHeader.Schema, header);
    }
    if (header instanceof RecordBatch$1) {
      return new Message2(bodyLength, MetadataVersion.V5, MessageHeader.RecordBatch, header);
    }
    if (header instanceof DictionaryBatch$1) {
      return new Message2(bodyLength, MetadataVersion.V5, MessageHeader.DictionaryBatch, header);
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
    return this.headerType === MessageHeader.Schema;
  }
  isRecordBatch() {
    return this.headerType === MessageHeader.RecordBatch;
  }
  isDictionaryBatch() {
    return this.headerType === MessageHeader.DictionaryBatch;
  }
  constructor(bodyLength, version, headerType, header) {
    this._version = version;
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
  constructor(length, nodes, buffers, compression) {
    this._nodes = nodes;
    this._buffers = buffers;
    this._length = bigIntToNumber(length);
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
  constructor(offset, length) {
    this.offset = bigIntToNumber(offset);
    this.length = bigIntToNumber(length);
  }
}
class FieldNode2 {
  constructor(length, nullCount) {
    this.length = bigIntToNumber(length);
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
      case MessageHeader.Schema:
        return Schema2.fromJSON(message);
      case MessageHeader.RecordBatch:
        return RecordBatch$1.fromJSON(message);
      case MessageHeader.DictionaryBatch:
        return DictionaryBatch$1.fromJSON(message);
    }
    throw new Error(`Unrecognized Message type: { name: ${MessageHeader[type]}, type: ${type} }`);
  });
}
function decodeMessageHeader(message, type) {
  return (() => {
    switch (type) {
      case MessageHeader.Schema:
        return Schema2.decode(message.header(new Schema$1()), /* @__PURE__ */ new Map(), message.version());
      case MessageHeader.RecordBatch:
        return RecordBatch$1.decode(message.header(new RecordBatch$2()), message.version());
      case MessageHeader.DictionaryBatch:
        return DictionaryBatch$1.decode(message.header(new DictionaryBatch$2()), message.version());
    }
    throw new Error(`Unrecognized Message type: { name: ${MessageHeader[type]}, type: ${type} }`);
  });
}
Field2["encode"] = encodeField;
Field2["decode"] = decodeField$1;
Field2["fromJSON"] = fieldFromJSON;
Schema2["encode"] = encodeSchema;
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
BodyCompression2["decode"] = decodeBodyCompression$1;
function decodeSchema$1(_schema, dictionaries = /* @__PURE__ */ new Map(), version = MetadataVersion.V5) {
  const fields = decodeSchemaFields$1(_schema, dictionaries);
  return new Schema2(fields, decodeCustomMetadata(_schema), dictionaries, version);
}
function decodeRecordBatch$1(batch, version = MetadataVersion.V5) {
  const recordBatch = new RecordBatch$1(batch.length(), decodeFieldNodes(batch), decodeBuffers(batch, version), decodeBodyCompression$1(batch.compression()));
  return recordBatch;
}
function decodeDictionaryBatch$1(batch, version = MetadataVersion.V5) {
  return new DictionaryBatch$1(RecordBatch$1.decode(batch.data(), version), batch.id(), batch.isDelta());
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
function decodeBuffers(batch, version) {
  const bufferRegions = [];
  for (let b, i = -1, j = -1, n = batch.buffersLength(); ++i < n; ) {
    if (b = batch.buffers(i)) {
      if (version < MetadataVersion.V4) {
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
  let keys;
  let dictType;
  let dictMeta;
  if (!dictionaries || !(dictMeta = f.dictionary())) {
    type = decodeFieldType(f, decodeFieldChildren$1(f, dictionaries));
    field2 = new Field2(f.name(), type, f.nullable(), decodeCustomMetadata(f));
  } else if (!dictionaries.has(id = bigIntToNumber(dictMeta.id()))) {
    keys = (keys = dictMeta.indexType()) ? decodeIndexType(keys) : new Int32();
    dictionaries.set(id, type = decodeFieldType(f, decodeFieldChildren$1(f, dictionaries)));
    dictType = new Dictionary(type, keys, id, dictMeta.isOrdered());
    field2 = new Field2(f.name(), dictType, f.nullable(), decodeCustomMetadata(f));
  } else {
    keys = (keys = dictMeta.indexType()) ? decodeIndexType(keys) : new Int32();
    dictType = new Dictionary(dictionaries.get(id), keys, id, dictMeta.isOrdered());
    field2 = new Field2(f.name(), dictType, f.nullable(), decodeCustomMetadata(f));
  }
  return field2 || null;
}
function decodeCustomMetadata(parent) {
  const data2 = /* @__PURE__ */ new Map();
  if (parent) {
    for (let entry, key, i = -1, n = Math.trunc(parent.customMetadataLength()); ++i < n; ) {
      if ((entry = parent.customMetadata(i)) && (key = entry.key()) != null) {
        data2.set(key, entry.value());
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
    case Type$1["NONE"]:
      return new Null2();
    case Type$1["Null"]:
      return new Null2();
    case Type$1["Binary"]:
      return new Binary2();
    case Type$1["LargeBinary"]:
      return new LargeBinary2();
    case Type$1["Utf8"]:
      return new Utf82();
    case Type$1["LargeUtf8"]:
      return new LargeUtf82();
    case Type$1["Bool"]:
      return new Bool2();
    case Type$1["List"]:
      return new List2((children || [])[0]);
    case Type$1["Struct_"]:
      return new Struct(children || []);
  }
  switch (typeId) {
    case Type$1["Int"]: {
      const t = f.type(new Int());
      return new Int_(t.isSigned(), t.bitWidth());
    }
    case Type$1["FloatingPoint"]: {
      const t = f.type(new FloatingPoint());
      return new Float(t.precision());
    }
    case Type$1["Decimal"]: {
      const t = f.type(new Decimal$1());
      return new Decimal2(t.scale(), t.precision(), t.bitWidth());
    }
    case Type$1["Date"]: {
      const t = f.type(new Date$1());
      return new Date_(t.unit());
    }
    case Type$1["Time"]: {
      const t = f.type(new Time());
      return new Time_(t.unit(), t.bitWidth());
    }
    case Type$1["Timestamp"]: {
      const t = f.type(new Timestamp());
      return new Timestamp_(t.unit(), t.timezone());
    }
    case Type$1["Interval"]: {
      const t = f.type(new Interval());
      return new Interval_(t.unit());
    }
    case Type$1["Duration"]: {
      const t = f.type(new Duration$1());
      return new Duration2(t.unit());
    }
    case Type$1["Union"]: {
      const t = f.type(new Union());
      return new Union_(t.mode(), t.typeIdsArray() || [], children || []);
    }
    case Type$1["FixedSizeBinary"]: {
      const t = f.type(new FixedSizeBinary$1());
      return new FixedSizeBinary2(t.byteWidth());
    }
    case Type$1["FixedSizeList"]: {
      const t = f.type(new FixedSizeList$1());
      return new FixedSizeList2(t.listSize(), (children || [])[0]);
    }
    case Type$1["Map"]: {
      const t = f.type(new Map$1());
      return new Map_((children || [])[0], t.keysSorted());
    }
  }
  throw new Error(`Unrecognized type: "${Type$1[typeId]}" (${typeId})`);
}
function decodeBodyCompression$1(b) {
  return b ? new BodyCompression2(b.codec(), b.method()) : null;
}
function encodeSchema(b, schema) {
  const fieldOffsets = schema.fields.map((f) => Field2.encode(b, f));
  Schema$1.startFieldsVector(b, fieldOffsets.length);
  const fieldsVectorOffset = Schema$1.createFieldsVector(b, fieldOffsets);
  const metadataOffset = !(schema.metadata && schema.metadata.size > 0) ? -1 : Schema$1.createCustomMetadataVector(b, [...schema.metadata].map(([k, v]) => {
    const key = b.createString(`${k}`);
    const val = b.createString(`${v}`);
    KeyValue.startKeyValue(b);
    KeyValue.addKey(b, key);
    KeyValue.addValue(b, val);
    return KeyValue.endKeyValue(b);
  }));
  Schema$1.startSchema(b);
  Schema$1.addFields(b, fieldsVectorOffset);
  Schema$1.addEndianness(b, platformIsLittleEndian ? Endianness.Little : Endianness.Big);
  if (metadataOffset !== -1) {
    Schema$1.addCustomMetadata(b, metadataOffset);
  }
  return Schema$1.endSchema(b);
}
function encodeField(b, field2) {
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
    const key = b.createString(`${k}`);
    const val = b.createString(`${v}`);
    KeyValue.startKeyValue(b);
    KeyValue.addKey(b, key);
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
    return sync ? decodeUtf8(this.toUint8Array(true)) : this.toUint8Array(false).then(decodeUtf8);
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
  constructor(source) {
    if (source) {
      this.source = new ByteStreamSource(streamAdapters.fromIterable(source));
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
  constructor(source) {
    if (source instanceof AsyncByteStream) {
      this.source = source.source;
    } else if (source instanceof AsyncByteQueue) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromAsyncIterable(source));
    } else if (isReadableNodeStream(source)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromNodeStream(source));
    } else if (isReadableDOMStream(source)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromDOMStream(source));
    } else if (isFetchResponse(source)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromDOMStream(source.body));
    } else if (isIterable(source)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromIterable(source));
    } else if (isPromise(source)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromAsyncIterable(source));
    } else if (isAsyncIterable(source)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromAsyncIterable(source));
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
  constructor(source) {
    this.source = source;
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
  constructor(source) {
    this.source = source;
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
    const buf = this.buffer;
    const end = Math.min(this.size, position + nBytes);
    return buf ? buf.subarray(position, end) : new Uint8Array(nBytes);
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
        let pos = position, offset = 0, bytesRead = 0;
        const end = Math.min(size, pos + Math.min(size - pos, nBytes));
        const buffer2 = new Uint8Array(Math.max(0, (this.position = end) - pos));
        while ((pos += bytesRead) < end && (offset += bytesRead) < buffer2.byteLength) {
          ({ bytesRead } = yield file.read(buffer2, offset, buffer2.byteLength - offset, pos));
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
    let product = L[3] * R[3];
    this.buffer[0] = product & 65535;
    let sum = product >>> 16;
    product = L[2] * R[3];
    sum += product;
    product = L[3] * R[2] >>> 0;
    sum += product;
    this.buffer[0] += sum << 16;
    this.buffer[1] = sum >>> 0 < product ? carryBit16 : 0;
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
    const length = str.length;
    const out = new Uint64(out_buffer);
    for (let posn = 0; posn < length; ) {
      const group = kInt32DecimalDigits < length - posn ? kInt32DecimalDigits : length - posn;
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
    const length = str.length;
    const out = new Int64(out_buffer);
    for (let posn = negate ? 1 : 0; posn < length; ) {
      const group = kInt32DecimalDigits < length - posn ? kInt32DecimalDigits : length - posn;
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
    let product = Uint64.multiply(L3, R3);
    this.buffer[0] = product.low();
    const sum = new Uint64(new Uint32Array([product.high(), 0]));
    product = Uint64.multiply(L2, R3);
    sum.plus(product);
    product = Uint64.multiply(L3, R2);
    sum.plus(product);
    this.buffer[1] = sum.low();
    this.buffer[3] = sum.lessThan(product) ? 1 : 0;
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
    const length = str.length;
    const out = new Int128(out_buffer);
    for (let posn = negate ? 1 : 0; posn < length; ) {
      const group = kInt32DecimalDigits < length - posn ? kInt32DecimalDigits : length - posn;
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
  const length = objects.length;
  const array = new Int32Array(length * 2);
  for (let oi = 0, ai = 0; oi < length; oi++) {
    const interval2 = objects[oi];
    array[ai++] = (_a2 = interval2["days"]) !== null && _a2 !== void 0 ? _a2 : 0;
    array[ai++] = (_b2 = interval2["milliseconds"]) !== null && _b2 !== void 0 ? _b2 : 0;
  }
  return array;
}
function toIntervalMonthDayNanoInt32Array(objects) {
  var _a2, _b2;
  const length = objects.length;
  const data2 = new Int32Array(length * 4);
  for (let oi = 0, ai = 0; oi < length; oi++) {
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
  visitNull(type, { length } = this.nextFieldNode()) {
    return makeData({ type, length });
  }
  visitBool(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitInt(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitFloat(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitUtf8(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitLargeUtf8(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitBinary(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitLargeBinary(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitFixedSizeBinary(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitDate(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitTimestamp(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitTime(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitDecimal(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitList(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), "child": this.visit(type.children[0]) });
  }
  visitStruct(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), children: this.visitMany(type.children) });
  }
  visitUnion(type, { length, nullCount } = this.nextFieldNode()) {
    if (this.metadataVersion < MetadataVersion.V5) {
      this.readNullBitmap(type, nullCount);
    }
    return type.mode === UnionMode.Sparse ? this.visitSparseUnion(type, { length, nullCount }) : this.visitDenseUnion(type, { length, nullCount });
  }
  visitDenseUnion(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, typeIds: this.readTypeIds(type), valueOffsets: this.readOffsets(type), children: this.visitMany(type.children) });
  }
  visitSparseUnion(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, typeIds: this.readTypeIds(type), children: this.visitMany(type.children) });
  }
  visitDictionary(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type.indices), dictionary: this.readDictionary(type) });
  }
  visitInterval(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitDuration(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitFixedSizeList(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), "child": this.visit(type.children[0]) });
  }
  visitMap(type, { length, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), "child": this.visit(type.children[0]) });
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
  readData(_type, { length, offset } = this.nextBufferRange()) {
    return this.bytes.subarray(offset, offset + length);
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
  readNullBitmap(_type, nullCount, { offset } = this.nextBufferRange()) {
    return nullCount <= 0 ? new Uint8Array(0) : packBools(this.sources[offset]);
  }
  readOffsets(_type, { offset } = this.nextBufferRange()) {
    return toArrayBufferView(Uint8Array, toArrayBufferView(_type.OffsetArrayType, this.sources[offset]));
  }
  readTypeIds(type, { offset } = this.nextBufferRange()) {
    return toArrayBufferView(Uint8Array, toArrayBufferView(type.ArrayType, this.sources[offset]));
  }
  readData(type, { offset } = this.nextBufferRange()) {
    const { sources } = this;
    if (DataType.isTimestamp(type)) {
      return toArrayBufferView(Uint8Array, Int64.convertArray(sources[offset]));
    } else if ((DataType.isInt(type) || DataType.isTime(type)) && type.bitWidth === 64 || DataType.isDuration(type)) {
      return toArrayBufferView(Uint8Array, Int64.convertArray(sources[offset]));
    } else if (DataType.isDate(type) && type.unit === DateUnit.MILLISECOND) {
      return toArrayBufferView(Uint8Array, Int64.convertArray(sources[offset]));
    } else if (DataType.isDecimal(type)) {
      return toArrayBufferView(Uint8Array, Int128.convertArray(sources[offset]));
    } else if (DataType.isBinary(type) || DataType.isLargeBinary(type) || DataType.isFixedSizeBinary(type)) {
      return binaryDataFromJSON(sources[offset]);
    } else if (DataType.isBool(type)) {
      return packBools(sources[offset]);
    } else if (DataType.isUtf8(type) || DataType.isLargeUtf8(type)) {
      return encodeUtf8(sources[offset].join(""));
    } else if (DataType.isInterval(type)) {
      switch (type.unit) {
        case IntervalUnit.DAY_TIME:
          return toIntervalDayTimeInt32Array(sources[offset]);
        case IntervalUnit.MONTH_DAY_NANO:
          return toIntervalMonthDayNanoInt32Array(sources[offset]);
      }
    }
    return toArrayBufferView(Uint8Array, toArrayBufferView(type.ArrayType, sources[offset].map((x) => +x)));
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
    const length = child === null || child === void 0 ? void 0 : child.length;
    if (length >= batchLength) {
      if (length === batchLength) {
        children[i] = child;
      } else {
        children[i] = child.slice(0, batchLength);
        memo.numBatches = Math.max(memo.numBatches, columns2[i].unshift(child.slice(batchLength, length - batchLength)));
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
          const keys = Object.keys(x);
          const vecs = keys.map((k) => new Vector([x[k]]));
          const batchSchema = schema !== null && schema !== void 0 ? schema : new Schema2(keys.map((k, i) => new Field2(String(k), vecs[i].type, vecs[i].nullable)));
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
  indexOf(element, offset) {
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
  getChild(name) {
    return this.getChildAt(this.schema.fields.findIndex((f) => f.name === name));
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
        const empty = makeData({ type, length: 0, nullCount: 0 });
        data2.push(empty._changeLengthAndBackfillNullBitmap(this.numRows));
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
  setChild(name, child) {
    var _b2;
    return this.setChildAt((_b2 = this.schema.fields) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name), child);
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
  proto["get"] = wrapChunkedCall1(instance$4.getVisitFn(Type.Struct));
  proto["set"] = wrapChunkedCall2(instance$5.getVisitFn(Type.Struct));
  proto["indexOf"] = wrapChunkedIndexOf(instance$3.getVisitFn(Type.Struct));
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
        const { fields, children, length } = Object.keys(obj).reduce((memo, name, i) => {
          memo.children[i] = obj[name];
          memo.length = Math.max(memo.length, obj[name].length);
          memo.fields[i] = Field2.new({ name, type: obj[name].type, nullable: true });
          return memo;
        }, {
          length: 0,
          fields: new Array(),
          children: new Array()
        });
        const schema = new Schema2(fields);
        const data2 = makeData({ type: new Struct(fields), length, children, nullCount: 0 });
        [this.schema, this.data] = ensureSameLengthData(schema, data2.children, length);
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
  indexOf(element, offset) {
    return instance$3.visit(this.data, element, offset);
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
  getChild(name) {
    var _b2;
    return this.getChildAt((_b2 = this.schema.fields) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name));
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
  setChild(name, child) {
    var _b2;
    return this.setChildAt((_b2 = this.schema.fields) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name), child);
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
    for (const name of columnNames) {
      const index = this.schema.fields.findIndex((f) => f.name === name);
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
const invalidMessageType$1 = (type) => `Expected ${MessageHeader[type]} Message in stream, but was null or length 0.`;
const nullMessage = (type) => `Header pointer of flatbuffer-encoded ${MessageHeader[type]} Message is null or length 0.`;
const invalidMessageMetadata$1 = (expected, actual) => `Expected to read ${expected} metadata bytes, but only read ${actual}.`;
const invalidMessageBodyLength$1 = (expected, actual) => `Expected to read ${expected} bytes for message body, but only read ${actual}.`;
class MessageReader {
  constructor(source) {
    this.source = source instanceof ByteStream ? source : new ByteStream(source);
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
    const buf = toUint8Array(this.source.read(bodyLength));
    if (buf.byteLength < bodyLength) {
      throw new Error(invalidMessageBodyLength$1(bodyLength, buf.byteLength));
    }
    return (
      /* 1. */
      buf.byteOffset % 8 === 0 && /* 2. */
      buf.byteOffset + buf.byteLength <= buf.buffer.byteLength ? buf : buf.slice()
    );
  }
  readSchema(throwIfNull = false) {
    const type = MessageHeader.Schema;
    const message = this.readMessage(type);
    const schema = message === null || message === void 0 ? void 0 : message.header();
    if (throwIfNull && !schema) {
      throw new Error(nullMessage(type));
    }
    return schema;
  }
  readMetadataLength() {
    const buf = this.source.read(PADDING);
    const bb = buf && new ByteBuffer$2(buf);
    const len = (bb === null || bb === void 0 ? void 0 : bb.readInt32(0)) || 0;
    return { done: len === 0, value: len };
  }
  readMetadata(metadataLength) {
    const buf = this.source.read(metadataLength);
    if (!buf) {
      return ITERATOR_DONE;
    }
    if (buf.byteLength < metadataLength) {
      throw new Error(invalidMessageMetadata$1(metadataLength, buf.byteLength));
    }
    return { done: false, value: Message2.decode(buf) };
  }
}
class AsyncMessageReader {
  constructor(source, byteLength) {
    this.source = source instanceof AsyncByteStream ? source : isFileHandle(source) ? new AsyncRandomAccessFile(source, byteLength) : new AsyncByteStream(source);
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
      const buf = toUint8Array(yield this.source.read(bodyLength));
      if (buf.byteLength < bodyLength) {
        throw new Error(invalidMessageBodyLength$1(bodyLength, buf.byteLength));
      }
      return (
        /* 1. */
        buf.byteOffset % 8 === 0 && /* 2. */
        buf.byteOffset + buf.byteLength <= buf.buffer.byteLength ? buf : buf.slice()
      );
    });
  }
  readSchema() {
    return __awaiter(this, arguments, void 0, function* (throwIfNull = false) {
      const type = MessageHeader.Schema;
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
      const buf = yield this.source.read(PADDING);
      const bb = buf && new ByteBuffer$2(buf);
      const len = (bb === null || bb === void 0 ? void 0 : bb.readInt32(0)) || 0;
      return { done: len === 0, value: len };
    });
  }
  readMetadata(metadataLength) {
    return __awaiter(this, void 0, void 0, function* () {
      const buf = yield this.source.read(metadataLength);
      if (!buf) {
        return ITERATOR_DONE;
      }
      if (buf.byteLength < metadataLength) {
        throw new Error(invalidMessageMetadata$1(metadataLength, buf.byteLength));
      }
      return { done: false, value: Message2.decode(buf) };
    });
  }
}
class JSONMessageReader extends MessageReader {
  constructor(source) {
    super(new Uint8Array(0));
    this._schema = false;
    this._body = [];
    this._batchIndex = 0;
    this._dictionaryIndex = 0;
    this._json = source instanceof ArrowJSON ? source : new ArrowJSON(source);
  }
  next() {
    const { _json } = this;
    if (!this._schema) {
      this._schema = true;
      const message = Message2.fromJSON(_json.schema, MessageHeader.Schema);
      return { done: false, value: message };
    }
    if (this._dictionaryIndex < _json.dictionaries.length) {
      const batch = _json.dictionaries[this._dictionaryIndex++];
      this._body = batch["data"]["columns"];
      const message = Message2.fromJSON(batch, MessageHeader.DictionaryBatch);
      return { done: false, value: message };
    }
    if (this._batchIndex < _json.batches.length) {
      const batch = _json.batches[this._batchIndex++];
      this._body = batch["columns"];
      const message = Message2.fromJSON(batch, MessageHeader.RecordBatch);
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
    const type = MessageHeader.Schema;
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
const MAGIC = new Uint8Array(MAGIC_STR.length);
for (let i = 0; i < MAGIC_STR.length; i += 1) {
  MAGIC[i] = MAGIC_STR.codePointAt(i);
}
function checkForMagicArrowString(buffer2, index = 0) {
  for (let i = -1, n = MAGIC.length; ++i < n; ) {
    if (MAGIC[i] !== buffer2[index + i]) {
      return false;
    }
  }
  return true;
}
const magicLength = MAGIC.length;
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
const LENGTH_NO_COMPRESSED_DATA$1 = -1;
const COMPRESS_LENGTH_PREFIX$1 = 8;
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
  static from(source) {
    if (source instanceof RecordBatchReader) {
      return source;
    } else if (isArrowJSON(source)) {
      return fromArrowJSON(source);
    } else if (isFileHandle(source)) {
      return fromFileHandle(source);
    } else if (isPromise(source)) {
      return (() => __awaiter(this, void 0, void 0, function* () {
        return yield RecordBatchReader.from(yield source);
      }))();
    } else if (isFetchResponse(source) || isReadableDOMStream(source) || isReadableNodeStream(source) || isAsyncIterable(source)) {
      return fromAsyncByteStream(new AsyncByteStream(source));
    }
    return fromByteStream(new ByteStream(source));
  }
  /** @nocollapse */
  static readAll(source) {
    if (source instanceof RecordBatchReader) {
      return source.isSync() ? readAllSync(source) : readAllAsync(source);
    } else if (isArrowJSON(source) || ArrayBuffer.isView(source) || isIterable(source) || isIteratorResult(source)) {
      return readAllSync(source);
    }
    return readAllAsync(source);
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
  _loadVectors(header, body, types) {
    return new VectorLoader(body, header.nodes, header.buffers, this.dictionaries, this.schema.metadataVersion).visitMany(types);
  }
  _loadCompressedVectors(header, body, types) {
    return new CompressedVectorLoader(body, header.nodes, header.buffers, this.dictionaries, this.schema.metadataVersion).visitMany(types);
  }
  _decompressBuffers(header, body, codec) {
    const decompressedBuffers = [];
    const newBufferRegions = [];
    let currentOffset = 0;
    for (const { offset, length } of header.buffers) {
      if (length === 0) {
        decompressedBuffers.push(new Uint8Array(0));
        newBufferRegions.push(new BufferRegion(currentOffset, 0));
        continue;
      }
      const byteBuf = new ByteBuffer$2(body.subarray(offset, offset + length));
      const uncompressedLenth = bigIntToNumber(byteBuf.readInt64(0));
      const bytes = byteBuf.bytes().subarray(COMPRESS_LENGTH_PREFIX$1);
      const decompressed = uncompressedLenth === LENGTH_NO_COMPRESSED_DATA$1 ? bytes : codec.decode(bytes);
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
  constructor(source, dictionaries) {
    super(dictionaries);
    this._reader = !isArrowJSON(source) ? new MessageReader(this._handle = source) : new JSONMessageReader(this._handle = source);
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
  constructor(source, dictionaries) {
    super(dictionaries);
    this._reader = new AsyncMessageReader(this._handle = source);
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
  constructor(source, dictionaries) {
    super(source instanceof RandomAccessFile ? source : new RandomAccessFile(source), dictionaries);
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
      const message = this._reader.readMessage(MessageHeader.RecordBatch);
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
      const message = this._reader.readMessage(MessageHeader.DictionaryBatch);
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
    const offset = _handle.size - magicAndPadding;
    const length = _handle.readInt32(offset);
    const buffer2 = _handle.readAt(offset - length, length);
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
  constructor(source, ...rest) {
    const byteLength = typeof rest[0] !== "number" ? rest.shift() : void 0;
    const dictionaries = rest[0] instanceof Map ? rest.shift() : void 0;
    super(source instanceof AsyncRandomAccessFile ? source : new AsyncRandomAccessFile(source, byteLength), dictionaries);
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
        const message = yield this._reader.readMessage(MessageHeader.RecordBatch);
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
        const message = yield this._reader.readMessage(MessageHeader.DictionaryBatch);
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
      const offset = _handle.size - magicAndPadding;
      const length = yield _handle.readInt32(offset);
      const buffer2 = yield _handle.readAt(offset - length, length);
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
  constructor(source, dictionaries) {
    super(source, dictionaries);
  }
  _loadVectors(header, body, types) {
    return new JSONVectorLoader(body, header.nodes, header.buffers, this.dictionaries, this.schema.metadataVersion).visitMany(types);
  }
}
function shouldAutoDestroy(self, options) {
  return options && typeof options["autoDestroy"] === "boolean" ? options["autoDestroy"] : self["autoDestroy"];
}
function* readAllSync(source) {
  const reader = RecordBatchReader.from(source);
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
function readAllAsync(source) {
  return __asyncGenerator(this, arguments, function* readAllAsync_1() {
    const reader = yield __await(RecordBatchReader.from(source));
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
function fromArrowJSON(source) {
  return new RecordBatchStreamReader(new RecordBatchJSONReaderImpl(source));
}
function fromByteStream(source) {
  const bytes = source.peek(magicLength + 7 & -8);
  return bytes && bytes.byteLength >= 4 ? !checkForMagicArrowString(bytes) ? new RecordBatchStreamReader(new RecordBatchStreamReaderImpl(source)) : new RecordBatchFileReader(new RecordBatchFileReaderImpl(source.read())) : new RecordBatchStreamReader(new RecordBatchStreamReaderImpl((function* () {
  })()));
}
function fromAsyncByteStream(source) {
  return __awaiter(this, void 0, void 0, function* () {
    const bytes = yield source.peek(magicLength + 7 & -8);
    return bytes && bytes.byteLength >= 4 ? !checkForMagicArrowString(bytes) ? new AsyncRecordBatchStreamReader(new AsyncRecordBatchStreamReaderImpl(source)) : new RecordBatchFileReader(new RecordBatchFileReaderImpl(yield source.read())) : new AsyncRecordBatchStreamReader(new AsyncRecordBatchStreamReaderImpl((function() {
      return __asyncGenerator(this, arguments, function* () {
      });
    })()));
  });
}
function fromFileHandle(source) {
  return __awaiter(this, void 0, void 0, function* () {
    const { size } = yield source.stat();
    const file = new AsyncRandomAccessFile(source, size);
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
      const { length } = data2;
      if (length > 2147483647) {
        throw new RangeError("Cannot write arrays larger than 2^31 - 1 in length");
      }
      if (DataType.isUnion(type)) {
        this.nodes.push(new FieldNode2(length, 0));
      } else {
        const { nullCount } = data2;
        if (!DataType.isNull(type)) {
          addBuffer.call(this, nullCount <= 0 ? new Uint8Array(0) : truncateBitmap(data2.offset, length, data2.nullBitmap));
        }
        this.nodes.push(new FieldNode2(length, nullCount));
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
  const { type, length, typeIds, valueOffsets } = data2;
  addBuffer.call(this, typeIds);
  if (type.mode === UnionMode.Sparse) {
    return assembleNestedVector.call(this, data2);
  } else if (type.mode === UnionMode.Dense) {
    if (data2.offset <= 0) {
      addBuffer.call(this, valueOffsets);
      return assembleNestedVector.call(this, data2);
    } else {
      const shiftedOffsets = new Int32Array(length);
      const childOffsets = /* @__PURE__ */ Object.create(null);
      const childLengths = /* @__PURE__ */ Object.create(null);
      for (let typeId, shift, index = -1; ++index < length; ) {
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
        return child.slice(childOffset, Math.min(length, childLength));
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
  const { length, values: values2, valueOffsets } = data2;
  const begin = bigIntToNumber(valueOffsets[0]);
  const end = bigIntToNumber(valueOffsets[length]);
  const byteLength = Math.min(end - begin, values2.byteLength - begin);
  addBuffer.call(this, rebaseValueOffsets(-begin, length + 1, valueOffsets));
  addBuffer.call(this, values2.subarray(begin, begin + byteLength));
  return this;
}
function assembleListVector(data2) {
  const { length, valueOffsets } = data2;
  if (valueOffsets) {
    const { [0]: begin, [length]: end } = valueOffsets;
    addBuffer.call(this, rebaseValueOffsets(-begin, length + 1, valueOffsets));
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
    isObject(options) || (options = { autoDestroy: true, writeLegacyIpcFormat: false, compressionType: null });
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
    } else if (isIterable(payload)) {
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
    if (message.headerType === MessageHeader.RecordBatch) {
      this._recordBatchBlocks.push(new FileBlock(alignedSize, message.bodyLength, this._position));
    } else if (message.headerType === MessageHeader.DictionaryBatch) {
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
    return this._write(MAGIC);
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
      const byteLength = isCompressionEffective ? finalBuffer.length : LENGTH_NO_COMPRESSED_DATA$1;
      const lengthPrefix = new ByteBuffer$2(new Uint8Array(COMPRESS_LENGTH_PREFIX$1));
      lengthPrefix.writeInt64(0, BigInt(byteLength));
      compressedBuffers.push(lengthPrefix.bytes(), new Uint8Array(finalBuffer));
      const padding = (currentOffset + 7 & -8) - currentOffset;
      currentOffset += padding;
      const fullBodyLength = COMPRESS_LENGTH_PREFIX$1 + finalBuffer.length;
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
      for (const buf of bufs)
        this._write(buf);
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
      const offset = (_b2 = this._dictionaryDeltaOffsets.get(id)) !== null && _b2 !== void 0 ? _b2 : 0;
      if (!prevDictionary || prevDictionary.data[0] !== chunks[0]) {
        for (const [index, chunk] of chunks.entries())
          this._writeDictionaryBatch(chunk, id, index > 0);
      } else if (offset < chunks.length) {
        for (const chunk of chunks.slice(offset))
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
function uniqueName(names, name) {
  names = isMapOrSet(names) ? names : new Set(names);
  let uname = name;
  let index = 0;
  while (names.has(uname)) {
    uname = name + ++index;
  }
  return uname;
}
function repeat(reps, value2) {
  const result2 = Array(reps);
  if (isFunction$1(value2)) {
    for (let i = 0; i < reps; ++i) {
      result2[i] = value2(i);
    }
  } else {
    result2.fill(value2);
  }
  return result2;
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
  const has = {};
  const ops = [];
  function add(name, params = []) {
    const key = name + ":" + params;
    if (has[key]) return has[key];
    const def = getAggregate(name);
    const op = def.create(...params);
    if (stream < 0 && def.stream) {
      def.stream.forEach((name2) => add(name2, []));
    }
    if (def.req) {
      def.req.forEach((name2) => add(name2, []));
    }
    has[key] = op;
    ops.push(op);
    return op;
  }
  const output2 = oplist.map((item) => {
    const op = add(item.name, item.params);
    op.output = item.id;
    return op;
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
    this._op.forEach((op) => op.init(state));
    if (state.values) {
      state.list = new ValueList$1();
    }
    return state;
  }
  write(state, values2, index) {
    const op = this._outputs;
    const n = op.length;
    for (let i = 0; i < n; ++i) {
      values2[op[i].output][index] = op[i].value(state);
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
    const { keys } = table2.groups() || {};
    const result2 = aggregate(table2, ops);
    const op = keys ? (name, row) => result2[name][keys[row]] : (name) => result2[name][0];
    get2 = get2.map((f) => (row) => f(row, data2, op));
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
  for (const op of ops) {
    const key = op.fields.map((f) => f + "").join(",");
    (fields[key] || (fields[key] = [])).push(op);
  }
  for (const key in fields) {
    aggrs.push(fieldReducer(fields[key], stream));
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
  const { keys, size } = groups;
  const cells = repeat(size, () => reducer.init());
  const data2 = table2.data();
  if (table2.isOrdered()) {
    const idx = table2.indices();
    const m = idx.length;
    for (let i = 0; i < m; ++i) {
      const row = idx[i];
      reducer.add(cells[keys[row]], row, data2);
    }
  } else if (table2.isFiltered()) {
    const bits = table2.mask();
    for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
      reducer.add(cells[keys[i]], i, data2);
    }
  } else {
    const n = table2.totalRows();
    for (let i = 0; i < n; ++i) {
      reducer.add(cells[keys[i]], i, data2);
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
function toFunction(value2) {
  return isFunction$1(value2) ? value2 : () => value2;
}
const ERROR_ESC_AGGRONLY = "Escaped functions are not valid as rollup or pivot values.";
function parseEscape(ctx, spec, params) {
  if (ctx.aggronly) error(ERROR_ESC_AGGRONLY);
  const code = `(row,data)=>fn(${rowObjectCode(ctx.table)},$)`;
  return { escape: compile.escape(code, toFunction(spec.expr), params) };
}
const ANNOTATE = { [Column$1]: 1, [Op]: 1 };
function parse(input, opt2 = {}) {
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
    op(op) {
      const key = opKey(op);
      return opcall[key] || (op.id = ++opId, opcall[key] = op);
    },
    field(node) {
      const code = generate(node);
      return fields[code] || (fields[code] = ++fieldId);
    },
    param(node) {
      return is(Literal, node) ? node.value : compiler.param(generate(node), params);
    },
    value(name, node) {
      names.push(name);
      const e = node.escape || (opt2.ast ? clean(node) : compileExpr(generate(node), params));
      exprs.push(e);
      if (ANNOTATE[node.type] && e !== node && isObject$1(e)) {
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
  for (const [name, value2] of entries(input)) {
    ctx.value(
      name + "",
      value2.escape ? parseEscape(ctx, value2, params) : parseExpression(ctx, value2)
    );
  }
  if (opt2.ast) {
    return { names, exprs };
  }
  const f = [];
  for (const key in fields) {
    f[fields[key]] = compiler.expr(key, params);
  }
  const ops = Object.values(opcall);
  ops.forEach((op) => op.fields = op.fields.map((id) => f[id]));
  return { names, exprs, ops };
}
function opKey(op) {
  let key = `${op.name}(${op.fields.concat(op.params).join(",")})`;
  if (op.frame) {
    const frame = op.frame.map((v) => Number.isFinite(v) ? Math.abs(v) : -1);
    key += `[${frame},${!!op.peers}]`;
  }
  return key;
}
function getParams(opt2) {
  return (opt2.table ? getTableParams(opt2.table) : opt2.join ? {
    ...getTableParams(opt2.join[1]),
    ...getTableParams(opt2.join[0])
  } : {}) || {};
}
function getTableParams(table2) {
  return table2 && isFunction$1(table2.params) ? table2.params() : {};
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
      ...isFunction$1(this.expr) ? { func: true } : {}
    };
  }
}
function field(expr, name, table2 = 0) {
  const props = table2 ? { field: true, table: table2 } : { field: true };
  return wrap$1(
    expr,
    name ? { expr: name, ...props } : props
  );
}
function assign$1(map, pairs2) {
  for (const [key, value2] of entries(pairs2)) {
    map.set(key, value2);
  }
  return map;
}
function resolve(table2, sel, map = /* @__PURE__ */ new Map()) {
  sel = isNumber$1(sel) ? table2.columnName(sel) : sel;
  if (isString(sel)) {
    map.set(sel, sel);
  } else if (isArray(sel)) {
    sel.forEach((r) => resolve(table2, r, map));
  } else if (isFunction$1(sel)) {
    resolve(table2, sel(table2), map);
  } else if (isObject$1(sel)) {
    assign$1(map, sel);
  } else {
    error(`Invalid column selection: ${toString(sel)}`);
  }
  return map;
}
function decorate(value2, toObject2) {
  value2.toObject = toObject2;
  return value2;
}
function toObject(value2) {
  return isArray(value2) ? value2.map(toObject) : value2 && value2.toObject ? value2.toObject() : value2;
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
      return table2.columnNames((name) => !drop.has(name));
    },
    () => ({ not: toObject(selection) })
  );
}
function parseValue(name, table2, params, options = { window: false }) {
  const exprs = /* @__PURE__ */ new Map();
  const marshal = (param) => {
    param = isNumber$1(param) ? table2.columnName(param) : param;
    isString(param) ? exprs.set(param, field(param)) : isFunction$1(param) ? resolve(table2, param).forEach(marshal) : isObject$1(param) ? assign$1(exprs, param) : error(`Invalid ${name} value: ${param + ""}`);
  };
  toArray(params).forEach(marshal);
  if (options.preparse) {
    options.preparse(exprs);
  }
  return parse(exprs, { table: table2, ...options });
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
  const keys = new Uint32Array(nrows);
  const index = {};
  const rows = [];
  const data2 = table2.data();
  const bits = table2.mask();
  if (bits) {
    for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
      const key = getKey(i, data2) + "";
      keys[i] = index[key] ??= rows.push(i) - 1;
    }
  } else {
    for (let i = 0; i < nrows; ++i) {
      const key = getKey(i, data2) + "";
      keys[i] = index[key] ??= rows.push(i) - 1;
    }
  }
  if (!ops.length) {
    get2 = get2.map((f) => (row) => f(row, data2));
  }
  return { keys, get: get2, names, rows, size: rows.length };
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
  add(name, values2) {
    if (!this.has(name)) this.names.push(name + "");
    return this.data[name] = values2;
  }
  /**
   * Test if this column set has a columns with the given name.
   * @param {string} name A column name
   * @return {boolean} True if this set contains a column with the given name,
   *  false otherwise.
   */
  has(name) {
    return Object.hasOwn(this.data, name);
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
  return _rollup(table2, parse(values2, { table: table2, aggronly: true, window: false }));
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
  const op = (id, row) => result2[id][row];
  const n = names.length;
  for (let i = 0; i < n; ++i) {
    const get2 = exprs[i];
    if (get2.field != null) {
      cols.add(names[i], result2[get2.field]);
    } else if (size > 1) {
      const col = cols.add(names[i], Array(size));
      for (let j = 0; j < size; ++j) {
        col[j] = get2(j, null, op);
      }
    } else {
      cols.add(names[i], [get2(0, null, op)]);
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
  const { keys, rows, size } = groups;
  const map = new Uint32Array(size);
  filter2.scan((row) => map[keys[row]] = 1);
  const sum = map.reduce((sum2, val) => sum2 + val, 0);
  if (sum === size) return groups;
  const _rows = Array(sum);
  let _size = 0;
  for (let i = 0; i < size; ++i) {
    if (map[i]) _rows[map[i] = _size++] = rows[i];
  }
  const _keys = new Uint32Array(keys.length);
  filter2.scan((row) => _keys[row] = map[keys[row]]);
  return { ...groups, keys: _keys, rows: _rows, size: _size };
}
function reindex(groups, scan2, filter2, nrows) {
  const { keys, rows, size } = groups;
  let _rows = rows;
  let _size = size;
  let map = null;
  if (filter2) {
    map = new Int32Array(size);
    scan2((row) => map[keys[row]] = 1);
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
  const fn = _size !== size ? (row) => _keys[++r] = map[keys[row]] : (row) => _keys[++r] = keys[row];
  scan2(fn);
  return { ...groups, keys: _keys, rows: _rows, size: _size };
}
function nest(table2, idx, obj, type) {
  const agg = type === "map" || type === true ? map_agg : type === "entries" ? entries_agg : type === "object" ? object_agg : error('groups option must be "map", "entries", or "object".');
  const { names } = table2.groups();
  const col = uniqueName(table2.columnNames(), "_");
  let t = select(table2, {}).reify(idx).create({ data: { [col]: obj } });
  t = rollup(t, { [col]: array_agg(col) });
  for (let i = names.length; --i >= 0; ) {
    t = rollup(
      groupby(t, names.slice(0, i)),
      // @ts-ignore
      { [col]: agg(names[i], col) }
    );
  }
  return t.get(col);
}
function arrayType$1(column) {
  return isTypedArray(column) ? column.constructor : Array;
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
  columnIndex(name) {
    return this._names.indexOf(name);
  }
  /**
   * Get the column instance with the given name.
   * @param {string} name The column name.
   * @return {import('./types.js').ColumnType | undefined}
   *  The named column, or undefined if it does not exist.
   */
  column(name) {
    return this._data[name];
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
  array(name, constructor = Array) {
    const column = this.column(name);
    const array = new constructor(this.numRows());
    let idx = -1;
    this.scan((row) => array[++idx] = column.at(row), true);
    return array;
  }
  /**
   * Get the value for the given column and row.
   * @param {string} name The column name.
   * @param {number} [row=0] The row index, defaults to zero if not specified.
   * @return {import('./types.js').DataValue} The table value at (column, row).
   */
  get(name, row = 0) {
    const column = this.column(name);
    return this.isFiltered() || this.isOrdered() ? column.at(this.indices()[row]) : column.at(row);
  }
  /**
   * Returns an accessor ("getter") function for a column. The returned
   * function takes a row index as its single argument and returns the
   * corresponding column value.
   * @param {string} name The column name.
   * @return {import('./types.js').ColumnGetter} The column getter function.
   */
  getter(name) {
    const column = this.column(name);
    const indices = this.isFiltered() || this.isOrdered() ? this.indices() : null;
    if (indices) {
      return (row) => column.at(indices[row]);
    } else if (column) {
      return (row) => column.at(row);
    } else {
      error(`Unrecognized column: ${name}`);
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
    const { grouped, limit, offset } = options;
    const names = resolve(this, options.columns || all());
    const createRow = rowObjectBuilder(this, names);
    const obj = [];
    this.scan(
      (row, data2) => obj.push(createRow(row, data2)),
      true,
      limit,
      offset
    );
    if (grouped && this.isGrouped()) {
      const idx = [];
      this.scan((row) => idx.push(row), true, limit, offset);
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
  *values(name) {
    const get2 = this.getter(name);
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
    const opt2 = isNumber$1(options) ? { limit: +options } : { ...options, limit: 10 };
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
    const { keys, size } = this._group;
    const part = repeat(size, () => []);
    const sort = this._index;
    const bits = this.mask();
    const n = this.numRows();
    if (sort && this.isOrdered()) {
      for (let i = 0, r; i < n; ++i) {
        r = sort[i];
        part[keys[r]].push(r);
      }
    } else if (bits) {
      for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
        part[keys[i]].push(i);
      }
    } else {
      for (let i = 0; i < n; ++i) {
        part[keys[i]].push(i);
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
        const name = names[i];
        const prev = this.column(name);
        const curr = data2[name] = new (arrayType$1(prev))(nrows);
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
  scan(fn, order, limit = Infinity, offset = 0) {
    const filter2 = this._mask;
    const nrows = this._nrows;
    const data2 = this._data;
    let i = offset || 0;
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
    input.columnNames((name) => cols.add(name, input.column(name)));
  });
  return cols.new(table2);
}
function concat(table2, ...others) {
  others = others.flat();
  const trows = table2.numRows();
  const nrows = trows + others.reduce((n, t) => n + t.numRows(), 0);
  if (trows === nrows) return table2;
  const tables = [table2, ...others];
  const cols = columnSet();
  table2.columnNames().forEach((name) => {
    const arr = Array(nrows);
    let row = 0;
    tables.forEach((table3) => {
      const col = table3.column(name) || { at: () => NULL };
      table3.scan((trow) => arr[row++] = col.at(trow));
    });
    cols.add(name, arr);
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
  table2.columnNames().forEach((name) => {
    const assign2 = !columns2.has(name);
    if (name === anchor) {
      if (aft && assign2) select2.set(name, name);
      for (const [key, value2] of columns2) {
        select2.set(key, value2);
      }
      if (aft) return;
    }
    if (assign2) select2.set(name, name);
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
const bisect = bisector(ascending);
function windowState(data2, frame, adjust, ops, aggrs) {
  let rows, peer, cells, result2, key;
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
      key = group;
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
          w.i0 = bisect.left(peer, peer[w.i0]);
        }
        if (w.i1 < n && isPeer(w.i1)) {
          w.i1 = bisect.right(peer, peer[w.i1 - 1]);
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
        aggr.write(cell, result2, key);
      }
      evaluate(w, result2, key);
      return result2;
    }
  };
  return w;
}
const frameValue = (op) => (op.frame || [null, null]).map((v) => Number.isFinite(v) ? Math.abs(v) : null);
const peersValue = (op) => !!op.peers;
function windowOp(spec) {
  const { id, name, fields = [], params = [] } = spec;
  return {
    ...getWindow(name).create(...params),
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
  table2.partitions().forEach((rows, key) => {
    const size = rows.length;
    const peers = windowPeers(table2, rows);
    for (let i = 0; i < nstate; ++i) {
      states[i].init(rows, peers, result2, key);
    }
    const op = (id) => result2[id][key];
    for (let index = 0; index < size; ++index) {
      for (let i = 0; i < nstate; ++i) {
        states[i].step(index);
      }
      write(rows[index], data2, op);
    }
  });
}
function windowStates(ops, data2) {
  const map = {};
  ops.forEach((op) => {
    const frame = frameValue(op);
    const peers = peersValue(op);
    const key = `${frame},${peers}`;
    const { aggOps, winOps } = map[key] || (map[key] = {
      frame,
      peers,
      aggOps: [],
      winOps: []
    });
    hasAggregate(op.name) ? aggOps.push(op) : winOps.push(windowOp(op));
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
function isWindowed(op) {
  return hasWindow(op.name) || op.frame && (Number.isFinite(op.frame[0]) || Number.isFinite(op.frame[1]));
}
function derive(table2, values2, options = {}) {
  const dt = _derive(table2, parse(values2, { table: table2 }), options);
  return options.drop || options.before == null && options.after == null ? dt : relocate(
    dt,
    Object.keys(values2).filter((name) => !table2.column(name)),
    options
  );
}
function _derive(table2, { names, exprs, ops = [] }, options = {}) {
  const total = table2.totalRows();
  const cols = columnSet(options.drop ? null : table2);
  const data2 = names.map((name) => cols.add(name, Array(total)));
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
    const op = ops[i];
    op.id = i;
    (isWindowed(op) ? winOps : aggOps).push(op);
  }
  return [aggOps, winOps];
}
function output$1(table2, cols, exprs, result2) {
  const bits = table2.mask();
  const data2 = table2.data();
  const { keys } = table2.groups() || {};
  const op = keys ? (id, row) => result2[id][keys[row]] : (id) => result2[id][0];
  const m = cols.length;
  for (let j = 0; j < m; ++j) {
    const get2 = exprs[j];
    const col = cols[j];
    if (bits) {
      for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
        col[i] = get2(i, data2, op);
      }
    } else {
      const n = table2.totalRows();
      for (let i = 0; i < n; ++i) {
        col[i] = get2(i, data2, op);
      }
    }
  }
}
function filter(table2, criteria) {
  const test = parse({ p: criteria }, { table: table2 });
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
function dedupe(table2, ...keys) {
  keys = keys.flat();
  const gt = groupby(table2, keys.length ? keys : table2.columnNames());
  return filter(gt, "row_number() === 1").ungroup().reify();
}
function rowLookup(table2, hash) {
  const lut = /* @__PURE__ */ new Map();
  table2.scan((row, data2) => {
    const key = hash(row, data2);
    if (key != null && key === key) {
      lut.set(key, row);
    }
  });
  return lut;
}
function indexLookup(idx, data2, hash) {
  const lut = /* @__PURE__ */ new Map();
  const n = idx.length;
  for (let i = 0; i < n; ++i) {
    const row = idx[i];
    const key = hash(row, data2);
    if (key != null && key === key) {
      lut.has(key) ? lut.get(key).push(i) : lut.set(key, [i]);
    }
  }
  return lut;
}
function intersect$1(a, b) {
  const set = new Set(b);
  return a.filter((x) => set.has(x));
}
function parseKey(name, table2, params) {
  const exprs = /* @__PURE__ */ new Map();
  toArray(params).forEach((param, i) => {
    param = isNumber$1(param) ? table2.columnName(param) : param;
    isString(param) ? exprs.set(i, field(param)) : isFunction$1(param) || isObject$1(param) && param.expr ? exprs.set(i, param) : error(`Invalid ${name} key value: ${param + ""}`);
  });
  const fn = parse(exprs, { table: table2, aggregate: false, window: false });
  return keyFunction(fn.exprs, true);
}
function inferKeys(tableL, tableR, on) {
  if (!on) {
    const isect = intersect$1(tableL.columnNames(), tableR.columnNames());
    if (!isect.length) error("Natural join requires shared column names.");
    on = [isect, isect];
  } else if (isString(on)) {
    on = [on, on];
  } else if (isArray(on) && on.length === 1) {
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
  const predicate = isArray(on) ? keyPredicate(tableL, tableR, ...on.map(toArray)) : parse({ on }, { join: [tableL, tableR] }).exprs[0];
  return _join_filter(tableL, tableR, predicate, options);
}
function _join_filter(tableL, tableR, predicate, options = {}) {
  const filter2 = new BitSet(tableL.totalRows());
  const join2 = isArray(predicate) ? hashSemiJoin : loopSemiJoin;
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
  table2.columnNames().forEach((name) => {
    if (!drop.has(name)) {
      const col = cols.add(name, []);
      if (!nset.has(name)) {
        priors.push(table2.column(name));
        copies.push(col);
      }
    }
  });
  names.forEach((name) => {
    if (!drop.has(name)) {
      if (!cols.has(name)) cols.add(name, []);
      unroll2.push(cols.data[name]);
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
      const array = toArray(fn(row, data2));
      const maxlen = Math.min(array.length, limit);
      copy(row, maxlen);
      for (let j = 0; j < maxlen; ++j) {
        col[start + j] = array[j];
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
  values2 = parse(values2, { table: table2 });
  values2.names.forEach(
    (name) => table2.column(name) ? 0 : error(`Invalid impute column ${toString(name)}`)
  );
  if (options.expand) {
    const opt2 = { preparse: preparse$1, window: false, aggronly: true };
    const params = parseValue("impute", table2, options.expand, opt2);
    const result2 = _rollup(ungroup(table2), params);
    return _impute(
      table2,
      values2,
      params.names,
      params.names.map((name) => result2.get(name, 0))
    );
  } else {
    return _impute(table2, values2);
  }
}
function preparse$1(map) {
  map.forEach(
    (value2, key) => value2.field ? map.set(key, array_agg_distinct(value2 + "")) : 0
  );
}
function _impute(table2, values2, keys, arrays) {
  const write = keys && keys.length;
  table2 = write ? expand(table2, keys, arrays) : table2;
  const { names, exprs, ops } = values2;
  const gets = aggregateGet(table2, ops, exprs);
  const cols = write ? null : columnSet(table2);
  const rows = table2.totalRows();
  names.forEach((name, i) => {
    const col = table2.column(name);
    const out = write ? col : cols.add(name, Array(rows));
    const get2 = gets[i];
    table2.scan((idx) => {
      const v = col.at(idx);
      out[idx] = !isValid(v) ? get2(idx) : v;
    });
  });
  return write ? table2 : table2.create(cols);
}
function expand(table2, keys, values2) {
  const groups = table2.groups();
  const data2 = table2.data();
  const keyNames = (groups ? groups.names : []).concat(keys);
  const keyGet = (groups ? groups.get : []).concat(keys.map((key) => table2.getter(key)));
  const hash = /* @__PURE__ */ new Set();
  const keyTable = keyFunction(keyGet);
  table2.scan((idx, data3) => hash.add(keyTable(idx, data3)));
  const names = table2.columnNames();
  const cols = columnSet();
  const out = names.map((name) => cols.add(name, []));
  names.forEach((name, i) => {
    const old = data2[name];
    const col = out[i];
    table2.scan((row) => col.push(old.at(row)));
  });
  const keyEnum = keyFunction(keyGet.map((k, i) => (a) => a[i]));
  const set = unroll$1(
    "v",
    "{" + out.map((_, i) => `_${i}.push(v[$${i}]);`).join("") + "}",
    out,
    names.map((name) => keyNames.indexOf(name))
  );
  if (groups) {
    let row = groups.keys.length;
    const prod = values2.reduce((p, a) => p * a.length, groups.size);
    const keys2 = new Uint32Array(prod + (row - hash.size));
    keys2.set(groups.keys);
    enumerate(groups, values2, (vec, idx) => {
      if (!hash.has(keyEnum(vec))) {
        set(vec);
        keys2[row++] = idx[0];
      }
    });
    cols.groupby({ ...groups, keys: keys2 });
  } else {
    enumerate(groups, values2, (vec) => {
      if (!hash.has(keyEnum(vec))) set(vec);
    });
  }
  return cols.new(table2);
}
function enumerate(groups, values2, callback) {
  const offset = groups ? groups.get.length : 0;
  const pad = groups ? 1 : 0;
  const len = pad + values2.length;
  const lens = new Int32Array(len);
  const idxs = new Int32Array(len);
  const set = [];
  if (groups) {
    const { get: get2, rows, size } = groups;
    lens[0] = size;
    set.push((vec2, idx) => {
      const row = rows[idx];
      for (let i = 0; i < offset; ++i) {
        vec2[i] = get2[i](row);
      }
    });
  }
  values2.forEach((a, i) => {
    const j = i + offset;
    lens[i + pad] = a.length;
    set.push((vec2, idx) => vec2[j] = a[idx]);
  });
  const vec = Array(offset + values2.length);
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
  if (isArray(on)) {
    const [onL, onR] = on.map(toArray);
    predicate = keyPredicate(tableL, tableR, onL, onR);
    if (!values2) {
      values2 = inferValues(tableL, onL, onR, options);
    }
  } else {
    predicate = parse({ on }, optParse).exprs[0];
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
        const c = `[${toString(s)}]`;
        return shared.has(s) ? { [s]: `(a, b) => a${c} == null ? b${c} : a${c}` } : s;
      }),
      vR
    ];
  }
  return options.right ? [vR, all()] : [all(), vR];
}
function parseValues$1(tableL, tableR, values2, optParse, suffix = []) {
  if (isArray(values2)) {
    let vL, vR, vJ, n = values2.length;
    vL = vR = vJ = { names: [], exprs: [] };
    if (n--) {
      vL = parseValue("join", tableL, values2[0], optParse);
    }
    if (n--) {
      vR = parseValue("join", tableR, values2[1], OPT_R);
    }
    if (n--) {
      vJ = parse(values2[2], optParse);
    }
    const rename2 = /* @__PURE__ */ new Set();
    const namesL = new Set(vL.names);
    vR.names.forEach((name) => {
      if (namesL.has(name)) {
        rename2.add(name);
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
    return parse(values2, optParse);
  }
}
function rekey(names, rename2, suffix) {
  names.forEach((name, i) => rename2.has(name) ? names[i] = name + suffix : 0);
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
  const join2 = isArray(predicate) ? hashJoin : loopJoin;
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
  names.forEach((name) => cols.add(name, Array(total).fill(NULL)));
  const lut = rowLookup(tableR, keyR);
  const set = unroll$1(
    ["lr", "rr", "data"],
    "{" + concat$1(names, (_, i) => `_[${i}][lr] = $[${i}](rr, data);`) + "}",
    names.map((name) => cols.data[name]),
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
  let keys = null, opA = "0", opB = "0";
  if (table2.isGrouped()) {
    keys = table2.groups().keys;
    opA = "ka";
    opB = "kb";
  }
  const { ops } = parse(fields, {
    table: table2,
    value: (name, node) => {
      names.push(name);
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
  const op = (id, row) => result2[id][row];
  const n = names.length;
  let code = "return (a, b) => {" + (op && table2.isGrouped() ? "const ka = keys[a], kb = keys[b];" : "") + "let u, v; return ";
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
  return Function("op", "keys", "fn", "data", code)(op, keys, fn, table2.data());
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
    if (isObject$1(expr) && !isFunction$1(expr)) {
      for (const key in expr) add(expr[key]);
    } else {
      add(
        isNumber$1(expr) ? field(param, table2.columnName(expr)) : isString(expr) ? field(param) : isFunction$1(expr) ? param : error(`Invalid orderby field: ${param + ""}`)
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
    (value2, key) => value2.field ? map.set(key, any(value2 + "")) : 0
  );
}
const opt = (value2, defaultValue) => value2 != null ? value2 : defaultValue;
function _pivot(table2, on, values2, options = {}) {
  const { keys, keyColumn } = pivotKeys(table2, on, options);
  const vsep = opt(options.valueSeparator, "_");
  const namefn = values2.names.length > 1 ? (i, name) => name + vsep + keys[i] : (i) => keys[i];
  const results = keys.map(
    (k) => aggregate(table2, values2.ops.map((op) => {
      if (op.name === "count") {
        const fn = (r) => k === keyColumn[r] ? 1 : NaN;
        fn.toString = () => k + ":1";
        return { ...op, name: "sum", fields: [fn] };
      }
      const fields = op.fields.map((f) => {
        const fn = (r, d) => k === keyColumn[r] ? f(r, d) : NaN;
        fn.toString = () => k + ":" + f;
        return fn;
      });
      return { ...op, fields };
    }))
  );
  return output(values2, namefn, table2.groups(), results).new(table2);
}
function pivotKeys(table2, on, options) {
  const limit = options.limit > 0 ? +options.limit : Infinity;
  const sort = opt(options.sort, true);
  const ksep = opt(options.keySeparator, "_");
  const get2 = aggregateGet(table2, on.ops, on.exprs);
  const key = get2.length === 1 ? get2[0] : (row, data2) => get2.map((fn) => fn(row, data2)).join(ksep);
  const kcol = Array(table2.totalRows());
  table2.scan((row, data2) => kcol[row] = key(row, data2));
  const uniq = aggregate(
    ungroup(table2),
    [{
      id: 0,
      name: "array_agg_distinct",
      fields: [((row) => kcol[row])],
      params: []
    }]
  )[0][0];
  const keys = sort ? uniq.sort() : uniq;
  return {
    keys: Number.isFinite(limit) ? keys.slice(0, limit) : keys,
    keyColumn: kcol
  };
}
function output({ names, exprs }, namefn, groups, results) {
  const size = groups ? groups.size : 1;
  const cols = columnSet();
  const m = results.length;
  const n = names.length;
  let result2;
  const op = (id, row) => result2[id][row];
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
          col[k] = get2(k, null, op);
        }
      }
    } else {
      for (let j = 0; j < m; ++j) {
        result2 = results[j];
        cols.add(namefn(j, names[i]), [get2(0, null, op)]);
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
  names.forEach((name) => cols.add(name, null));
  const cells = groups ? reduceGroups(table2, reducer, groups) : [reduceFlat(table2, reducer)];
  reducer.outputs().map((name) => cols.add(name, []));
  const n = counts.length - 1;
  let len = 0;
  for (let i = 0; i < n; ++i) {
    len += counts[i + 1] = reducer.write(cells[i], cols.data, counts[i]);
  }
  if (groups) {
    const data2 = table2.data();
    names.forEach((name, index) => {
      const column = cols.data[name] = Array(len);
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
function sample$1(buffer2, replace, index, weight) {
  return (replace ? weight ? sampleRW : sampleRU : weight ? sampleNW : sampleNU)(buffer2.length, buffer2, index, weight);
}
function sampleRU(size, buffer2, index) {
  const n = index.length;
  for (let i = 0; i < size; ++i) {
    buffer2[i] = index[n * random() | 0];
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
    buffer2[i] = index[bisect2(w, sum * random())];
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
    const j = i * random();
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
    w[i] = -Math.log(random()) / weight(index[i]);
  }
  k.sort((a, b) => w[a] - w[b]);
  for (let i = 0; i < size; ++i) {
    buffer2[i] = index[k[i]];
  }
  return buffer2;
}
function shuffle(array, lo = 0, hi = array.length) {
  let n = hi - (lo = +lo);
  while (n) {
    const i = random() * n-- | 0;
    const v = array[n + lo];
    array[n + lo] = array[i + lo];
    array[i + lo] = v;
  }
  return array;
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
  return isNumber$1(size) ? () => size : get(_rollup(table2, parse({ size }, { table: table2, window: false })).column("size"));
}
function parseWeight(table2, w) {
  if (w == null) return null;
  w = isNumber$1(w) ? table2.columnName(w) : w;
  return get(
    isString(w) ? table2.column(w) : _derive(table2, parse({ w }, { table: table2 }), { drop: true }).column("w")
  );
}
function _sample(table2, size, weight, options = {}) {
  const { replace, shuffle: shuffle$1 } = options;
  const parts = table2.partitions(false);
  let total = 0;
  size = parts.map((idx, group) => {
    let s = size(group);
    total += s = replace ? s : Math.min(idx.length, s);
    return s;
  });
  const samples = new Uint32Array(total);
  let curr = 0;
  parts.forEach((idx, group) => {
    const sz = size[group];
    const buf = samples.subarray(curr, curr += sz);
    if (!replace && sz === idx.length) {
      buf.set(idx);
    } else {
      sample$1(buf, replace, idx, weight);
    }
  });
  if (shuffle$1 !== false && (parts.length > 1 || !replace)) {
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
  const map = names.reduce((map2, name, i) => map2.set(name, i), /* @__PURE__ */ new Map());
  const add = (index, name) => {
    const columns2 = spreadCols(table2, get2[index], limit);
    const n = columns2.length;
    for (let i = 0; i < n; ++i) {
      cols.add(as[i] || `${name}_${i + 1}`, columns2[i]);
    }
  };
  table2.columnNames().forEach((name) => {
    if (map.has(name)) {
      if (!drop) cols.add(name, table2.column(name));
      add(map.get(name), name);
      map.delete(name);
    } else {
      cols.add(name, table2.column(name));
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
function union(table2, ...others) {
  return dedupe(concat(table2, others.flat()));
}
function unorder(table2) {
  return table2.isOrdered() ? table2.create({ order: null }) : table2;
}
const SIZEOF_INT = 4;
const SIZEOF_SHORT = 2;
function decodeBit(bitmap2, index) {
  return (bitmap2[index >> 3] & 1 << index % 8) !== 0;
}
function readObject(buf, index) {
  const pos = index + readInt32(buf, index);
  const vtable = pos - readInt32(buf, pos);
  const size = readInt16(buf, vtable);
  return (index2, read, fallback = null) => {
    if (index2 < size) {
      const off = readInt16(buf, vtable + index2);
      if (off) return read(buf, pos + off);
    }
    return fallback;
  };
}
function readOffset(buf, offset) {
  return offset;
}
function readBoolean(buf, offset) {
  return !!readInt8(buf, offset);
}
function readInt8(buf, offset) {
  return readUint8(buf, offset) << 24 >> 24;
}
function readUint8(buf, offset) {
  return buf[offset];
}
function readInt16(buf, offset) {
  return readUint16(buf, offset) << 16 >> 16;
}
function readUint16(buf, offset) {
  return buf[offset] | buf[offset + 1] << 8;
}
function readInt32(buf, offset) {
  return buf[offset] | buf[offset + 1] << 8 | buf[offset + 2] << 16 | buf[offset + 3] << 24;
}
function readUint32(buf, offset) {
  return readInt32(buf, offset) >>> 0;
}
function readInt64(buf, offset) {
  return toNumber(BigInt.asIntN(
    64,
    BigInt(readUint32(buf, offset)) + (BigInt(readUint32(buf, offset + SIZEOF_INT)) << 32n)
  ));
}
function readString(buf, index) {
  let offset = index + readInt32(buf, index);
  const length = readInt32(buf, offset);
  offset += SIZEOF_INT;
  return decodeUtf8$1(buf.subarray(offset, offset + length));
}
function readVector(buf, offset, stride, extract) {
  if (!offset) return [];
  const base = offset + readInt32(buf, offset);
  return Array.from(
    { length: readInt32(buf, base) },
    (_, i) => extract(buf, base + SIZEOF_INT + i * stride)
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
    length,
    nullCount,
    type,
    validity,
    values: values2,
    offsets,
    sizes,
    children
  }) {
    this.length = length;
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
    const { length, values: values2 } = this;
    this.values = values2.subarray(0, length);
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
    const sign = (-1) ** ((v & 32768) >> 15);
    switch (expo) {
      case 31:
        return sign * (sigf ? Number.NaN : 1 / 0);
      case 0:
        return sign * (sigf ? 6103515625e-14 * sigf : 0);
    }
    return sign * 2 ** (expo - 15) * (1 + sigf);
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
    return decodeUtf8$1(offset32(this, index));
  }
}
class LargeUtf8Batch extends ArrayBatch {
  /**
   * @param {number} index
   */
  value(index) {
    return decodeUtf8$1(offset64(this, index));
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
  const [keys, vals] = children[0].children;
  const start = offsets[index];
  const end = offsets[index + 1];
  const entries2 = [];
  for (let i = start; i < end; ++i) {
    entries2.push([keys.at(i), vals.at(i)]);
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
  value(index, offset = index) {
    const { typeIds, children, typeMap } = this;
    return children[typeMap[typeIds[index]]].at(offset);
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
      bisect$1(
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
    const offset = index << 4;
    let start = offset + 4;
    let buf = (
      /** @type {Uint8Array} */
      values2
    );
    const length = readInt32(buf, offset);
    if (length > 12) {
      start = readInt32(buf, offset + 12);
      buf = data2[readInt32(buf, offset + 8)];
    }
    return buf.subarray(start, start + length);
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
    return decodeUtf8$1(this.view(index));
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
    const i = bisect$1(offsets, index) - 1;
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
    const { length, nullCount, data: data2 } = this;
    const copy = !nullCount && isDirectBatch(data2[0]);
    const n = data2.length;
    if (copy && n === 1) {
      return data2[0].values;
    }
    const ArrayType = !n || nullCount > 0 ? Array : data2[0].constructor.ArrayType ?? data2[0].values.constructor;
    const array = new ArrayType(length);
    return copy ? copyArray(array, data2) : extractArray(array, data2);
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
function copyArray(array, data2) {
  for (let i = 0, offset = 0; i < data2.length; ++i) {
    const { values: values2 } = data2[i];
    array.set(values2, offset);
    offset += values2.length;
  }
  return array;
}
function extractArray(array, data2) {
  let index = -1;
  for (let i = 0; i < data2.length; ++i) {
    const batch = data2[i];
    for (let j = 0; j < batch.length; ++j) {
      array[++index] = batch.at(j);
    }
  }
  return array;
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
  getChild(name) {
    const i = this.names.findIndex((x) => x === name);
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
    const indices = names.map((name) => all2.indexOf(name));
    return this.selectAt(indices, as);
  }
  /**
   * Return an object mapping column names to extracted value arrays.
   * @returns {{ [P in keyof T]: ValueArray<T[P]> }}
   */
  toColumns() {
    const { children, names } = this;
    const cols = {};
    names.forEach((name, i) => cols[name] = children[i]?.toArray() ?? []);
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
    const b = bisect$1(offsets, index) - 1;
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
function renameField(field2, name) {
  return name != null && name !== field2.name ? { ...field2, name } : field2;
}
function batchType(type, options = {}) {
  const { typeId, bitWidth, mode, precision, unit } = (
    /** @type {any} */
    type
  );
  const { useBigInt, useDate, useDecimalInt, useMap, useProxy } = options;
  switch (typeId) {
    case Type$2.Null:
      return NullBatch;
    case Type$2.Bool:
      return BoolBatch;
    case Type$2.Int:
    case Type$2.Time:
    case Type$2.Duration:
      return useBigInt || bitWidth < 64 ? DirectBatch : Int64Batch;
    case Type$2.Float:
      return precision ? DirectBatch : Float16Batch;
    case Type$2.Date:
      return wrap(
        unit === DateUnit$1.DAY ? DateDayBatch : DateDayMillisecondBatch,
        useDate && DateBatch
      );
    case Type$2.Timestamp:
      return wrap(
        unit === TimeUnit$1.SECOND ? TimestampSecondBatch : unit === TimeUnit$1.MILLISECOND ? TimestampMillisecondBatch : unit === TimeUnit$1.MICROSECOND ? TimestampMicrosecondBatch : TimestampNanosecondBatch,
        useDate && DateBatch
      );
    case Type$2.Decimal:
      return bitWidth === 32 ? useDecimalInt ? DirectBatch : Decimal32NumberBatch : useDecimalInt ? DecimalBigIntBatch : DecimalNumberBatch;
    case Type$2.Interval:
      return unit === IntervalUnit$1.DAY_TIME ? IntervalDayTimeBatch : unit === IntervalUnit$1.YEAR_MONTH ? DirectBatch : IntervalMonthDayNanoBatch;
    case Type$2.FixedSizeBinary:
      return FixedBinaryBatch;
    case Type$2.Utf8:
      return Utf8Batch;
    case Type$2.LargeUtf8:
      return LargeUtf8Batch;
    case Type$2.Binary:
      return BinaryBatch;
    case Type$2.LargeBinary:
      return LargeBinaryBatch;
    case Type$2.BinaryView:
      return BinaryViewBatch;
    case Type$2.Utf8View:
      return Utf8ViewBatch;
    case Type$2.List:
      return ListBatch;
    case Type$2.LargeList:
      return LargeListBatch;
    case Type$2.Map:
      return useMap ? MapBatch : MapEntryBatch;
    case Type$2.ListView:
      return ListViewBatch;
    case Type$2.LargeListView:
      return LargeListViewBatch;
    case Type$2.FixedSizeList:
      return FixedListBatch;
    case Type$2.Struct:
      return useProxy ? StructProxyBatch : StructBatch;
    case Type$2.RunEndEncoded:
      return RunEndEncodedBatch;
    case Type$2.Dictionary:
      return DictionaryBatch3;
    case Type$2.Union:
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
function writeInt32(buf, index, value2) {
  buf[index] = value2;
  buf[index + 1] = value2 >> 8;
  buf[index + 2] = value2 >> 16;
  buf[index + 3] = value2 >> 24;
}
function writeInt64(buf, index, value2) {
  const v = BigInt(value2);
  writeInt32(buf, index + 4, Number(BigInt.asIntN(32, v >> BigInt(32))));
  writeInt32(buf, index + 0, Number(BigInt.asIntN(32, v)));
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
    writeInt64(this.buf, this.space -= 8, value2);
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
  addOffset(offset) {
    prep(this, SIZEOF_INT, 0);
    this.writeInt32(this.offset() - offset + SIZEOF_INT);
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
    const utf82 = encodeUtf8$1(s);
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
    const { buf, sink } = this;
    const bytes = buf.subarray(this.space, buf.length);
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
    const pad = (size + 7 & -8) - size;
    this.addPadding(pad);
    return size + pad;
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
  let { buf, space, minalign } = builder2;
  if (size > minalign) {
    builder2.minalign = size;
  }
  const bufSize = buf.length;
  const used = bufSize - space + additionalBytes;
  const alignSize = ~used + 1 & size - 1;
  buf = grow(buf, used + alignSize + size - 1, true);
  space += buf.length - bufSize;
  for (let i = 0; i < alignSize; ++i) {
    buf[--space] = 0;
  }
  builder2.buf = buf;
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
      const { buf, vtables, space: vt1 } = builder2;
      outer_loop:
        for (i = 0; i < vtables.length; ++i) {
          const vt2 = buf.length - vtables[i];
          if (len == readInt16(buf, vt2)) {
            for (let j = SIZEOF_SHORT; j < len; j += SIZEOF_SHORT) {
              if (readInt16(buf, vt1 + j) != readInt16(buf, vt2 + j)) {
                continue outer_loop;
              }
            }
            existingTable = vtables[i];
            break;
          }
        }
      if (existingTable) {
        builder2.space = buf.length - vtableOffset;
        writeInt32(buf, builder2.space, existingTable - vtableOffset);
      } else {
        const off = builder2.offset();
        vtables.push(off);
        writeInt32(buf, buf.length - vtableOffset, off - vtableOffset);
      }
      return vtableOffset;
    }
  };
}
const LENGTH_NO_COMPRESSED_DATA = -1;
const COMPRESS_LENGTH_PREFIX = 8;
function missingCodec(type) {
  return `Missing compression codec "${keyFor(CompressionType$1, type)}" (id ${type})`;
}
const codecs = /* @__PURE__ */ new Map();
function getCompressionCodec(type) {
  return type != null && codecs.get(type) || null;
}
function decompressBuffer(body, { offset, length }, codec) {
  if (length === 0) {
    return { bytes: new Uint8Array(0), offset: 0, length: 0 };
  }
  const ulen = readInt64(body, offset);
  const buf = body.subarray(offset + COMPRESS_LENGTH_PREFIX, offset + length);
  const bytes = ulen === LENGTH_NO_COMPRESSED_DATA ? buf : codec.decode(buf);
  return { bytes, offset: 0, length: bytes.length };
}
function compressBuffer(bytes, codec) {
  const compressed = codec.encode(bytes);
  const keep = compressed.length < bytes.length;
  const data2 = keep ? compressed : bytes;
  const buf = new Uint8Array(COMPRESS_LENGTH_PREFIX + data2.length);
  writeInt64(buf, 0, keep ? bytes.length : LENGTH_NO_COMPRESSED_DATA);
  buf.set(data2, COMPRESS_LENGTH_PREFIX);
  return buf;
}
function decodeBlock(buf, index) {
  return {
    offset: readInt64(buf, index),
    metadataLength: readInt32(buf, index + 8),
    bodyLength: readInt64(buf, index + 16)
  };
}
function decodeBlocks(buf, index) {
  return readVector(buf, index, 24, decodeBlock);
}
function decodeBodyCompression(buf, index) {
  const get2 = readObject(buf, index);
  return {
    codec: (
      /** @type {CompressionType_} */
      get2(4, readInt8, CompressionType$1.LZ4_FRAME)
    ),
    method: (
      /** @type {BodyCompressionMethod_} */
      get2(6, readInt8, BodyCompressionMethod$1.BUFFER)
    )
  };
}
function decodeRecordBatch(buf, index, version) {
  const get2 = readObject(buf, index);
  const offset = version < Version.V4 ? 8 : 0;
  return {
    length: get2(4, readInt64, 0),
    nodes: readVector(buf, get2(6, readOffset), 16, (buf2, pos) => ({
      length: readInt64(buf2, pos),
      nullCount: readInt64(buf2, pos + 8)
    })),
    regions: readVector(buf, get2(8, readOffset), 16 + offset, (buf2, pos) => ({
      offset: readInt64(buf2, pos + offset),
      length: readInt64(buf2, pos + offset + 8)
    })),
    compression: get2(10, decodeBodyCompression),
    variadic: readVector(buf, get2(12, readOffset), 8, readInt64)
  };
}
function decodeDictionaryBatch(buf, index, version) {
  const get2 = readObject(buf, index);
  return {
    id: get2(4, readInt64, 0),
    data: get2(6, (buf2, off) => decodeRecordBatch(buf2, off, version)),
    /**
     * If isDelta is true the values in the dictionary are to be appended to a
     * dictionary with the indicated id. If isDelta is false this dictionary
     * should replace the existing dictionary.
     */
    isDelta: get2(8, readBoolean, false)
  };
}
function decodeDataType(buf, index, typeId, children) {
  checkOneOf(typeId, Type$2, invalidDataType);
  const get2 = readObject(buf, index);
  switch (typeId) {
    // types without flatbuffer objects
    case Type$2.Binary:
      return binary();
    case Type$2.Utf8:
      return utf8();
    case Type$2.LargeBinary:
      return largeBinary();
    case Type$2.LargeUtf8:
      return largeUtf8();
    case Type$2.List:
      return list(children[0]);
    case Type$2.ListView:
      return listView(children[0]);
    case Type$2.LargeList:
      return largeList(children[0]);
    case Type$2.LargeListView:
      return largeListView(children[0]);
    case Type$2.Struct:
      return struct(children);
    case Type$2.RunEndEncoded:
      return runEndEncoded(children[0], children[1]);
    // types with flatbuffer objects
    case Type$2.Int:
      return int(
        // @ts-ignore
        get2(4, readInt32, 0),
        // bitwidth
        get2(6, readBoolean, false)
        // signed
      );
    case Type$2.Float:
      return float(
        // @ts-ignore
        get2(4, readInt16, Precision$1.HALF)
        // precision
      );
    case Type$2.Decimal:
      return decimal(
        get2(4, readInt32, 0),
        // precision
        get2(6, readInt32, 0),
        // scale
        // @ts-ignore
        get2(8, readInt32, 128)
        // bitwidth
      );
    case Type$2.Date:
      return date(
        // @ts-ignore
        get2(4, readInt16, DateUnit$1.MILLISECOND)
        // unit
      );
    case Type$2.Time:
      return time(
        // @ts-ignore
        get2(4, readInt16, TimeUnit$1.MILLISECOND)
        // unit
      );
    case Type$2.Timestamp:
      return timestamp(
        // @ts-ignore
        get2(4, readInt16, TimeUnit$1.SECOND),
        // unit
        get2(6, readString)
        // timezone
      );
    case Type$2.Interval:
      return interval(
        // @ts-ignore
        get2(4, readInt16, IntervalUnit$1.YEAR_MONTH)
        // unit
      );
    case Type$2.Duration:
      return duration(
        // @ts-ignore
        get2(4, readInt16, TimeUnit$1.MILLISECOND)
        // unit
      );
    case Type$2.FixedSizeBinary:
      return fixedSizeBinary(
        get2(4, readInt32, 0)
        // stride
      );
    case Type$2.FixedSizeList:
      return fixedSizeList(
        children[0],
        get2(4, readInt32, 0)
        // stride
      );
    case Type$2.Map:
      return mapType(
        get2(4, readBoolean, false),
        // keysSorted
        children[0]
      );
    case Type$2.Union:
      return union$1(
        // @ts-ignore
        get2(4, readInt16, UnionMode$1.Sparse),
        // mode
        children,
        readVector(buf, get2(6, readOffset), 4, readInt32)
        // type ids
      );
  }
  return { typeId };
}
function decodeMetadata(buf, index) {
  const entries2 = readVector(buf, index, 4, (buf2, pos) => {
    const get2 = readObject(buf2, pos);
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
function decodeSchema(buf, index, version) {
  const get2 = readObject(buf, index);
  return {
    version,
    endianness: (
      /** @type {Endianness_} */
      get2(4, readInt16, 0)
    ),
    fields: get2(6, decodeSchemaFields, []),
    metadata: get2(8, decodeMetadata)
  };
}
function decodeSchemaFields(buf, fieldsOffset) {
  return readVector(buf, fieldsOffset, 4, decodeField);
}
function decodeField(buf, index) {
  const get2 = readObject(buf, index);
  const typeId = get2(8, readUint8, Type$2.NONE);
  const typeOffset = get2(10, readOffset, 0);
  const dict = get2(12, decodeDictionary);
  const children = get2(14, decodeFieldChildren, []);
  let type = decodeDataType(buf, typeOffset, typeId, children);
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
function decodeFieldChildren(buf, fieldOffset) {
  return readVector(buf, fieldOffset, 4, decodeField);
}
function decodeDictionary(buf, index) {
  if (!index) return null;
  const get2 = readObject(buf, index);
  return dictionary$1(
    null,
    // data type will be populated by caller
    get2(6, decodeInt, int32$1()),
    // index type
    get2(8, readBoolean, false),
    // ordered
    get2(4, readInt64, 0)
    // id
  );
}
function decodeInt(buf, index) {
  return (
    /** @type {IntType} */
    decodeDataType(buf, index, Type$2.Int)
  );
}
const invalidMessageMetadata = (expected, actual) => `Expected to read ${expected} metadata bytes, but only read ${actual}.`;
const invalidMessageBodyLength = (expected, actual) => `Expected to read ${expected} bytes for message body, but only read ${actual}.`;
const invalidMessageType = (type) => `Unsupported message type: ${type} (${keyFor(MessageHeader$1, type)})`;
function decodeMessage(buf, index) {
  let metadataLength = readInt32(buf, index) || 0;
  index += SIZEOF_INT;
  if (metadataLength === -1) {
    metadataLength = readInt32(buf, index) || 0;
    index += SIZEOF_INT;
  }
  if (metadataLength === 0) return null;
  const head = buf.subarray(index, index += metadataLength);
  if (head.byteLength < metadataLength) {
    throw new Error(invalidMessageMetadata(metadataLength, head.byteLength));
  }
  const get2 = readObject(head, 0);
  const version = (
    /** @type {Version_} */
    get2(4, readInt16, Version.V1)
  );
  const type = (
    /** @type {MessageHeader_} */
    get2(6, readUint8, MessageHeader$1.NONE)
  );
  const offset = get2(8, readOffset, 0);
  const bodyLength = get2(10, readInt64, 0);
  let content;
  if (offset) {
    const decoder2 = type === MessageHeader$1.Schema ? decodeSchema : type === MessageHeader$1.DictionaryBatch ? decodeDictionaryBatch : type === MessageHeader$1.RecordBatch ? decodeRecordBatch : null;
    if (!decoder2) throw new Error(invalidMessageType(type));
    content = decoder2(head, offset, version);
    if (bodyLength > 0) {
      const body = buf.subarray(index, index += bodyLength);
      if (body.byteLength < bodyLength) {
        throw new Error(invalidMessageBodyLength(bodyLength, body.byteLength));
      }
      content.body = body;
    } else if (type !== MessageHeader$1.Schema) {
      content.body = new Uint8Array(0);
    }
  }
  return { version, type, index, content };
}
function decodeIPC(data2) {
  const source = isArrayBufferLike(data2) ? new Uint8Array(data2) : data2;
  return source instanceof Uint8Array && isArrowFileFormat(source) ? decodeIPCFile(source) : decodeIPCStream(source);
}
function isArrowFileFormat(buf) {
  if (!buf || buf.length < 4) return false;
  for (let i = 0; i < 6; ++i) {
    if (MAGIC$1[i] !== buf[i]) return false;
  }
  return true;
}
function decodeIPCStream(data2) {
  const stream = [data2].flat();
  let schema;
  const records = [];
  const dictionaries = [];
  for (const buf of stream) {
    if (!(buf instanceof Uint8Array)) {
      throw new Error(`IPC data batch was not a Uint8Array.`);
    }
    let offset = 0;
    while (true) {
      const m = decodeMessage(buf, offset);
      if (m === null) break;
      offset = m.index;
      if (!m.content) continue;
      switch (m.type) {
        case MessageHeader$1.Schema:
          if (!schema) schema = m.content;
          break;
        case MessageHeader$1.RecordBatch:
          records.push(m.content);
          break;
        case MessageHeader$1.DictionaryBatch:
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
  const offset = data2.byteLength - (MAGIC$1.length + 4);
  const length = readInt32(data2, offset);
  const get2 = readObject(data2, offset - length);
  const version = (
    /** @type {Version_} */
    get2(4, readInt16, Version.V1)
  );
  const dicts = get2(8, decodeBlocks, []);
  const recs = get2(10, decodeBlocks, []);
  return (
    /** @type {ArrowData} */
    {
      schema: get2(6, (buf, index) => decodeSchema(buf, index, version)),
      dictionaries: dicts.map(({ offset: offset2 }) => decodeMessage(data2, offset2).content),
      records: recs.map(({ offset: offset2 }) => decodeMessage(data2, offset2).content),
      metadata: get2(12, decodeMetadata)
    }
  );
}
function tableFromIPC(data2, options) {
  return createTable(decodeIPC(data2), options);
}
function createTable(data2, options = {}) {
  const { schema = { fields: [] }, dictionaries, records } = data2;
  const { version, fields } = schema;
  const dictionaryMap = /* @__PURE__ */ new Map();
  const context = contextGenerator(options, version, dictionaryMap);
  const dictionaryTypes = /* @__PURE__ */ new Map();
  visitSchemaFields(schema, (field2) => {
    const type = field2.type;
    if (type.typeId === Type$2.Dictionary) {
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
  dicts.forEach((value2, key) => dictionaryMap.set(key, value2.done()));
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
function contextGenerator(options, version, dictionaryMap) {
  const base = {
    version,
    options,
    dictionary: (id) => dictionaryMap.get(id)
  };
  return (batch) => {
    const { length, nodes, regions, compression, variadic, body } = batch;
    let nodeIndex = -1;
    let bufferIndex = -1;
    let variadicIndex = -1;
    return {
      ...base,
      length,
      node: () => nodes[++nodeIndex],
      buffer: (ArrayType) => {
        const { bytes, length: length2, offset } = maybeDecompress(body, regions[++bufferIndex], compression);
        return ArrayType ? new ArrayType(bytes.buffer, bytes.byteOffset + offset, length2 / ArrayType.BYTES_PER_ELEMENT) : bytes.subarray(offset, offset + length2);
      },
      variadic: () => variadic[++variadicIndex],
      visit(children) {
        return children.map((f) => visit$1(f.type, this));
      }
    };
  };
}
function maybeDecompress(body, region, compression) {
  if (!compression) {
    return { bytes: body, ...region };
  } else if (compression.method !== BodyCompressionMethod$1.BUFFER) {
    throw new Error(`Unknown compression method (${compression.method})`);
  } else {
    const id = compression.codec;
    const codec = getCompressionCodec(id);
    if (!codec) throw new Error(missingCodec(id));
    return decompressBuffer(body, region, codec);
  }
}
function visit$1(type, ctx) {
  const { typeId } = type;
  const { options, node, buffer: buffer2, variadic, version } = ctx;
  const BatchType = batchType(type, options);
  const base = { ...node(), type };
  if (typeId === Type$2.Null) {
    return new BatchType({ ...base, nullCount: base.length });
  }
  switch (typeId) {
    // validity and data value buffers
    case Type$2.Bool:
    case Type$2.Int:
    case Type$2.Time:
    case Type$2.Duration:
    case Type$2.Float:
    case Type$2.Decimal:
    case Type$2.Date:
    case Type$2.Timestamp:
    case Type$2.Interval:
    case Type$2.FixedSizeBinary:
      return new BatchType({
        ...base,
        validity: buffer2(),
        values: buffer2(type.values)
      });
    // validity, offset, and value buffers
    case Type$2.Utf8:
    case Type$2.LargeUtf8:
    case Type$2.Binary:
    case Type$2.LargeBinary:
      return new BatchType({
        ...base,
        validity: buffer2(),
        offsets: buffer2(type.offsets),
        values: buffer2()
      });
    // views with variadic buffers
    case Type$2.BinaryView:
    case Type$2.Utf8View:
      return new BatchType({
        ...base,
        validity: buffer2(),
        values: buffer2(),
        // views buffer
        data: Array.from({ length: variadic() }, () => buffer2())
        // data buffers
      });
    // validity, offset, and list child
    case Type$2.List:
    case Type$2.LargeList:
    case Type$2.Map:
      return new BatchType({
        ...base,
        validity: buffer2(),
        offsets: buffer2(type.offsets),
        children: ctx.visit(type.children)
      });
    // validity, offset, size, and list child
    case Type$2.ListView:
    case Type$2.LargeListView:
      return new BatchType({
        ...base,
        validity: buffer2(),
        offsets: buffer2(type.offsets),
        sizes: buffer2(type.offsets),
        children: ctx.visit(type.children)
      });
    // validity and children
    case Type$2.FixedSizeList:
    case Type$2.Struct:
      return new BatchType({
        ...base,
        validity: buffer2(),
        children: ctx.visit(type.children)
      });
    // children only
    case Type$2.RunEndEncoded:
      return new BatchType({
        ...base,
        children: ctx.visit(type.children)
      });
    // dictionary
    case Type$2.Dictionary: {
      const { id, indices } = type;
      return new BatchType({
        ...base,
        validity: buffer2(),
        values: buffer2(indices.values)
      }).setDictionary(ctx.dictionary(id));
    }
    // union
    case Type$2.Union: {
      if (version < Version.V5) {
        buffer2();
      }
      return new BatchType({
        ...base,
        typeIds: buffer2(int8Array),
        offsets: type.mode === UnionMode$1.Sparse ? null : buffer2(type.offsets),
        children: ctx.visit(type.children)
      });
    }
    // unsupported type
    default:
      throw new Error(invalidDataType(typeId));
  }
}
function encodeRecordBatch(builder2, batch, compression) {
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
    b.addOffset(3, encodeCompression(builder2, compression), 0);
    b.addOffset(4, variadicVector, 0);
  });
}
function encodeCompression(builder2, compression) {
  if (!compression) return 0;
  const { codec, method } = compression;
  return builder2.addObject(2, (b) => {
    b.addInt8(0, codec, CompressionType$1.LZ4_FRAME);
    b.addInt8(1, method, BodyCompressionMethod$1.BUFFER);
  });
}
function encodeDictionaryBatch(builder2, dictionaryBatch, compression) {
  const dataOffset = encodeRecordBatch(builder2, dictionaryBatch.data, compression);
  return builder2.addObject(3, (b) => {
    b.addInt64(0, dictionaryBatch.id, 0);
    b.addOffset(1, dataOffset, 0);
    b.addInt8(2, +dictionaryBatch.isDelta, 0);
  });
}
function writeFooter(builder2, schema, dictBlocks, recordBlocks, metadata) {
  const metadataOffset = encodeMetadata(builder2, metadata);
  const recsOffset = builder2.addVector(recordBlocks, 24, 8, encodeBlock);
  const dictsOffset = builder2.addVector(dictBlocks, 24, 8, encodeBlock);
  const schemaOffset = encodeSchema$1(builder2, schema);
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
  builder2.sink.write(MAGIC$1);
}
function encodeBlock(builder2, { offset, metadataLength, bodyLength }) {
  builder2.writeInt64(bodyLength);
  builder2.writeInt32(0);
  builder2.writeInt32(metadataLength);
  builder2.writeInt64(offset);
  return builder2.offset();
}
function writeMessage(builder2, headerType, headerOffset, bodyLength, blocks) {
  builder2.finish(
    builder2.addObject(5, (b) => {
      b.addInt16(0, Version.V5, Version.V1);
      b.addInt8(1, headerType, MessageHeader$1.NONE);
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
    const buf = new Uint8Array(size);
    for (let i = 0, off = 0; i < bufs.length; ++i) {
      buf.set(bufs[i], off);
      off += bufs[i].byteLength;
    }
    return buf;
  }
}
const STREAM = "stream";
const FILE = "file";
function encodeIPC(data2, { sink, format = STREAM, codec } = {}) {
  if (format !== STREAM && format !== FILE) {
    throw new Error(`Unrecognized Arrow IPC format: ${format}`);
  }
  const { schema, dictionaries = [], records = [], metadata } = data2;
  const builder2 = new Builder2(sink || new MemorySink());
  const file = format === FILE;
  const dictBlocks = [];
  const recordBlocks = [];
  const compression = codec != null ? { codec, method: BodyCompressionMethod$1.BUFFER } : null;
  if (file) {
    builder2.addBuffer(MAGIC$1);
  }
  if (schema) {
    writeMessage(
      builder2,
      MessageHeader$1.Schema,
      encodeSchema$1(builder2, schema),
      0
    );
  }
  for (const dict of dictionaries) {
    const { data: data3 } = dict;
    writeMessage(
      builder2,
      MessageHeader$1.DictionaryBatch,
      encodeDictionaryBatch(builder2, dict, compression),
      data3.byteLength,
      dictBlocks
    );
    writeBuffers(builder2, data3.buffers);
  }
  for (const batch of records) {
    writeMessage(
      builder2,
      MessageHeader$1.RecordBatch,
      encodeRecordBatch(builder2, batch, compression),
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
  const id = options?.codec;
  const codec = getCompressionCodec(id);
  if (id != null && !codec) throw new Error(missingCodec(id));
  const columns2 = table2.children;
  checkBatchLengths(columns2);
  const { dictionaries, idMap } = assembleDictionaryBatches(columns2, codec);
  const records = assembleRecordBatches(columns2, codec);
  const schema = assembleSchema(table2.schema, idMap);
  const data2 = { schema, dictionaries, records };
  return encodeIPC(data2, { ...options, codec: id }).finish();
}
function checkBatchLengths(columns2) {
  const n = columns2[0]?.data.map((d) => d.length);
  columns2.forEach(({ data: data2 }) => {
    if (data2.length !== n.length || data2.some((b, i) => b.length !== n[i])) {
      throw new Error("Columns have inconsistent batch sizes.");
    }
  });
}
function assembleContext(codec) {
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
    node(length, nullCount) {
      nodes.push({ length, nullCount });
    },
    /**
     * @param {TypedArray} b
     */
    buffer(b) {
      const bytes = new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
      const buf = codec ? compressBuffer(bytes, codec) : bytes;
      const length = buf.byteLength;
      regions.push({ offset: byteLength, length });
      buffers.push(buf);
      byteLength += length + 7 & -8;
    },
    /**
     * @param {number} length
     */
    variadic(length) {
      variadic.push(length);
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
function assembleDictionaryBatches(columns2, codec) {
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
          data: assembleRecordBatch([dictionaryColumn], i, codec)
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
  if (batch?.type.typeId === Type$2.Dictionary) {
    const dictionary2 = batch.dictionary;
    visitor(dictionary2);
    visitDictionaries(dictionary2.data[0], visitor);
  }
  batch?.children?.forEach((child) => visitDictionaries(child, visitor));
}
function assembleSchema(schema, idMap) {
  if (!idMap.size) return schema;
  const visit2 = (type) => {
    if (type.typeId === Type$2.Dictionary) {
      type.id = idMap.get(type.dictionary);
      visitDictType(type);
    }
    if (type.children) {
      (type.children = type.children.slice()).forEach(visitFields);
    }
  };
  const visitFields = (field2, index, array) => {
    const type = { ...field2.type };
    array[index] = { ...field2, type };
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
function assembleRecordBatches(columns2, codec) {
  return (columns2[0]?.data || []).map((_, index) => assembleRecordBatch(columns2, index, codec));
}
function assembleRecordBatch(columns2, batchIndex = 0, codec) {
  const ctx = assembleContext(codec);
  columns2.forEach((column) => {
    visit(column.type, column.data[batchIndex], ctx);
  });
  return ctx.done();
}
function visit(type, batch, ctx) {
  const { typeId } = type;
  ctx.node(batch.length, batch.nullCount);
  if (typeId === Type$2.Null) return;
  switch (typeId) {
    // validity and value buffers
    // backing dictionaries handled elsewhere
    case Type$2.Bool:
    case Type$2.Int:
    case Type$2.Time:
    case Type$2.Duration:
    case Type$2.Float:
    case Type$2.Date:
    case Type$2.Timestamp:
    case Type$2.Decimal:
    case Type$2.Interval:
    case Type$2.FixedSizeBinary:
    case Type$2.Dictionary:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.values);
      return;
    // validity, offset, and value buffers
    case Type$2.Utf8:
    case Type$2.LargeUtf8:
    case Type$2.Binary:
    case Type$2.LargeBinary:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.offsets);
      ctx.buffer(batch.values);
      return;
    // views with variadic buffers
    case Type$2.BinaryView:
    case Type$2.Utf8View:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.values);
      ctx.variadic(batch.data.length);
      batch.data.forEach((b) => ctx.buffer(b));
      return;
    // validity, offset, and list child
    case Type$2.List:
    case Type$2.LargeList:
    case Type$2.Map:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.offsets);
      ctx.children(type, batch);
      return;
    // validity, offset, size, and list child
    case Type$2.ListView:
    case Type$2.LargeListView:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.offsets);
      ctx.buffer(batch.sizes);
      ctx.children(type, batch);
      return;
    // validity and children
    case Type$2.FixedSizeList:
    case Type$2.Struct:
      ctx.buffer(batch.validity);
      ctx.children(type, batch);
      return;
    // children only
    case Type$2.RunEndEncoded:
      ctx.children(type, batch);
      return;
    // union
    case Type$2.Union: {
      ctx.buffer(batch.typeIds);
      if (type.mode === UnionMode$1.Dense) {
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
  const keys = /* @__PURE__ */ Object.create(null);
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
      let k = keys[v];
      if (k === void 0) {
        keys[v] = k = ++index;
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
  let length = 0;
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
      length++;
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
          } else if (isArray$1(value2)) {
            arrayCount++;
            const len = value2.length;
            if (len < minLength) minLength = len;
            if (len > maxLength) maxLength = len;
            arrayProfile ??= profiler();
            value2.forEach(arrayProfile.add);
          } else {
            structCount++;
            for (const key in value2) {
              const fieldProfiler = structProfiles[key] ?? (structProfiles[key] = profiler());
              fieldProfiler.add(value2[key]);
            }
          }
      }
    },
    type() {
      const valid = length - nullCount;
      return valid === 0 ? nullType() : intCount === valid ? intType(min2, max2) : numberCount === valid ? float64$1() : bigintCount === valid ? bigintType(minBigInt, maxBigInt) : boolCount === valid ? bool() : dayCount === valid ? dateDay() : dateCount === valid ? timestamp() : stringCount === valid ? dictionary$1(utf8()) : arrayCount === valid ? arrayType(arrayProfile.type(), minLength, maxLength) : structCount === valid ? struct(
        Object.entries(structProfiles).map((_) => field$1(_[0], _[1].type()))
      ) : unionType();
    }
  };
}
function arrayType(type, minLength, maxLength) {
  return maxLength === minLength ? fixedSizeList(type, minLength) : list(type);
}
function intType(min2, max2) {
  const v = Math.max(Math.abs(min2) - 1, max2);
  return v < 1 << 7 ? int8() : v < 1 << 15 ? int16() : v < 2 ** 31 ? int32$1() : float64$1();
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
      const name = type.children[i].name;
      return (value2, index) => child.set(value2?.[name], index);
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
    const [key, val] = this.children;
    key.set(value2[0], index);
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
      const key = keyString(value2);
      if (key !== this.key) {
        if (this.key) this.next();
        this.key = key;
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
    const length = this.index + 1;
    return {
      length,
      nullCount,
      type,
      typeIds: typeIds.array(length),
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
    const offset = child.index + 1;
    child.set(value2, offset);
    this.offsets.set(offset, index);
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
    super.set(value2 && encodeUtf8$1(value2), index);
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
    case Type$2.Int:
    case Type$2.Time:
    case Type$2.Duration:
      return isInt64ArrayType(type.values) ? new Int64Builder(type, ctx) : new DirectBuilder(type, ctx);
    case Type$2.Float:
      return type.precision ? new DirectBuilder(type, ctx) : new TransformBuilder(type, ctx, toFloat16);
    case Type$2.Binary:
    case Type$2.LargeBinary:
      return new BinaryBuilder(type, ctx);
    case Type$2.Utf8:
    case Type$2.LargeUtf8:
      return new Utf8Builder(type, ctx);
    case Type$2.Bool:
      return new BoolBuilder(type, ctx);
    case Type$2.Decimal:
      return type.bitWidth === 32 ? new TransformBuilder(type, ctx, toDecimal32(type.scale)) : new DecimalBuilder(type, ctx);
    case Type$2.Date:
      return new TransformBuilder(type, ctx, type.unit ? toBigInt : toDateDay);
    case Type$2.Timestamp:
      return new TransformBuilder(type, ctx, toTimestamp(type.unit));
    case Type$2.Interval:
      switch (type.unit) {
        case IntervalUnit$1.DAY_TIME:
          return new IntervalDayTimeBuilder(type, ctx);
        case IntervalUnit$1.MONTH_DAY_NANO:
          return new IntervalMonthDayNanoBuilder(type, ctx);
      }
      return new DirectBuilder(type, ctx);
    case Type$2.List:
    case Type$2.LargeList:
      return new ListBuilder(type, ctx);
    case Type$2.Struct:
      return new StructBuilder(type, ctx);
    case Type$2.Union:
      return type.mode ? new DenseUnionBuilder(type, ctx) : new SparseUnionBuilder(type, ctx);
    case Type$2.FixedSizeBinary:
      return new FixedSizeBinaryBuilder(type, ctx);
    case Type$2.FixedSizeList:
      return new FixedSizeListBuilder(type, ctx);
    case Type$2.Map:
      return new MapBuilder(type, ctx);
    case Type$2.RunEndEncoded:
      return new RunEndEncodedBuilder(type, ctx);
    case Type$2.Dictionary:
      return new DictionaryBuilder(type, ctx);
  }
  throw new Error(invalidDataType(typeId));
}
function columnFromValues(values2, type, options = {}, dicts) {
  const visit2 = isIterable$1(values2) ? (callback) => {
    for (const value2 of values2) callback(value2);
  } : values2;
  type ??= inferType$1(visit2);
  const { maxBatchRows = Infinity, ...opt2 } = options;
  let data2;
  if (type.typeId === Type$2.Null) {
    let length = 0;
    visit2(() => ++length);
    data2 = nullBatches(type, length, maxBatchRows);
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
function nullBatches(type, length, limit) {
  const data2 = [];
  const batch = (length2) => new NullBatch({ length: length2, nullCount: length2, type });
  const numBatches = Math.floor(length / limit);
  for (let i = 0; i < numBatches; ++i) {
    data2.push(batch(limit));
  }
  const rem = length % limit;
  if (rem) data2.push(batch(rem));
  return data2;
}
function columnFromArray(array, type, options = {}, dicts) {
  return !type && isTypedArray$1(array) ? columnFromTypedArray(array, options) : columnFromValues((v) => array.forEach(v), type, options, dicts);
}
function columnFromTypedArray(values2, { maxBatchRows, useBigInt }) {
  const arrayType2 = (
    /** @type {TypedArrayConstructor} */
    values2.constructor
  );
  const type = typeForTypedArray(arrayType2);
  const length = values2.length;
  const limit = Math.min(maxBatchRows || Infinity, length);
  const numBatches = Math.floor(length / limit);
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
  if (idx < length) add(idx, length);
  return new Column(batches);
}
function typeForTypedArray(arrayType2) {
  switch (arrayType2) {
    case float32Array:
      return float32$1();
    case float64Array:
      return float64$1();
    case int8Array:
      return int8();
    case int16Array:
      return int16();
    case int32Array:
      return int32$1();
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
  const length = entries2[0]?.[1].length;
  const columns2 = entries2.map(([name, col]) => {
    if (col.length !== length) {
      throw new Error("All columns must have the same length.");
    }
    fields.push(field$1(name, col.type));
    return col;
  });
  const schema = {
    version: Version.V5,
    endianness: Endianness$1.Little,
    fields,
    metadata: null
  };
  return new Table3(schema, columns2, useProxy);
}
function columns(table2, names) {
  return isFunction$1(names) ? names(table2) : names || table2.columnNames();
}
function toArrow(table2, options = {}) {
  const { columns: columns$1, limit = Infinity, offset = 0, types = {}, ...opt2 } = options;
  const names = columns(table2, columns$1);
  const data2 = table2.data();
  const fullScan = offset === 0 && table2.numRows() <= limit && !table2.isFiltered() && !table2.isOrdered();
  return tableFromColumns(names.map((name) => {
    const values2 = data2[name];
    const type = types[name];
    const isArray2 = isArrayType(values2);
    let col;
    if (fullScan && (isArray2 || isFunction$1(values2.toArray))) {
      col = columnFromArray(isArray2 ? values2 : values2.toArray(), type, opt2);
    } else {
      const get2 = isArray2 ? (row) => values2[row] : (row) => values2.at(row);
      col = columnFromValues(
        (visit2) => table2.scan((row) => visit2(get2(row)), true, limit, offset),
        type,
        opt2
      );
    }
    return [name, col];
  }));
}
function toArrowIPC(data2, options = {}) {
  const { format = "stream", ...toArrowOptions } = options;
  return tableToIPC(toArrow(data2, toArrowOptions), { format });
}
function identity(x) {
  return x;
}
function scan(table2, names, limit = 100, offset, ctx) {
  const { start = identity, cell, end = identity } = ctx;
  const data2 = table2.data();
  const n = names.length;
  table2.scan((row) => {
    start(row);
    for (let i = 0; i < n; ++i) {
      const name = names[i];
      cell(data2[name].at(row), name, i);
    }
    end(row);
  }, true, limit, offset);
}
function toCSV(table2, options = {}) {
  const names = columns(table2, options.columns);
  const format = options.format || {};
  const delim = options.delimiter || ",";
  const header = options.header ?? true;
  const reFormat = new RegExp(`["${delim}
\r]`);
  const formatValue2 = (value2) => value2 == null ? "" : isDate(value2) ? formatUTCDate(value2, true) : reFormat.test(value2 += "") ? '"' + value2.replace(/"/g, '""') + '"' : value2;
  const vals = names.map(formatValue2);
  let text = header ? vals.join(delim) + "\n" : "";
  scan(table2, names, options.limit || Infinity, options.offset, {
    cell(value2, name, index) {
      vals[index] = formatValue2(format[name] ? format[name](value2) : value2);
    },
    end() {
      text += vals.join(delim) + "\n";
    }
  });
  return text;
}
function mapObject(obj, fn, output2 = {}) {
  for (const key in obj) {
    output2[key] = fn(obj[key], key);
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
    if (type === "object" && isDate(value2)) {
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
  names.forEach((name) => {
    const auto = inferFormat(values(table2, name), options);
    align2[name] = alignOpt[name] || auto.align;
    format[name] = formatOpt[name] || auto.format;
  });
  return { align: align2, format };
}
function values(table2, columnName) {
  const column = table2.column(columnName);
  return (fn) => table2.scan((row) => fn(column.at(row)));
}
function formatValue(v, options = {}) {
  if (isFunction$1(options)) {
    return options(v) + "";
  }
  const type = typeof v;
  if (type === "object") {
    if (isDate(v)) {
      return options.utc ? formatUTCDate(v) : formatDate(v);
    } else {
      const s = JSON.stringify(
        v,
        // @ts-ignore
        (k, v2) => isTypedArray(v2) ? Array.from(v2) : v2
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
  const tag = (tag2, name, shouldAlign) => {
    const a = shouldAlign ? alignValue(align2[name]) : "";
    const s = style[tag2] ? style[tag2](name, idx, r) || "" : "";
    const css = (a ? `text-align: ${a};` + (s ? " " : "") : "") + s;
    return `<${tag2}${css ? ` style="${css}"` : ""}>`;
  };
  let text = tag("table") + tag("thead") + tag("tr", r) + names.map((name) => `${tag("th", name, 1)}${name}</th>`).join("") + "</tr></thead>" + tag("tbody");
  scan(table2, names, options.limit, options.offset, {
    start(row) {
      r = row;
      ++idx;
      text += tag("tr");
    },
    cell(value2, name) {
      text += tag("td", name, 1) + formatter(value2, format[name]) + "</td>";
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
    (value2) => isFunction$1(value2) ? value2 : () => value2
  );
}
const COLUMNS = "columns";
const NDJSON = "ndjson";
const defaultFormatter = (value2) => isDate(value2) ? formatUTCDate(value2, true) : value2;
function toJSON(table2, {
  type,
  columns: cols,
  format = {},
  limit,
  offset
} = {}) {
  const names = columns(table2, cols);
  const fmt = names.map((name) => format[name] || defaultFormatter);
  const scan2 = (fn) => table2.scan(fn, true, limit, offset);
  return type === COLUMNS ? toColumns(table2, names, fmt, scan2) : toRows(table2, names, fmt, scan2, type === NDJSON);
}
function toColumns(table2, names, format, scan2) {
  let text = "{";
  names.forEach((name, i) => {
    text += (i ? "," : "") + JSON.stringify(name) + ":[";
    const column = table2.column(name);
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
  const keys = names.map((name) => `"${name}":`);
  const cols = names.map((name) => table2.column(name));
  const finish = nd ? (o) => o.replaceAll("\n", "") : identity;
  const sep = nd ? "\n" : ",";
  let text = nd ? "" : "[";
  let r = -1;
  scan2((row) => {
    const props = [];
    for (let i = 0; i < n; ++i) {
      props.push(keys[i] + JSON.stringify(format[i](cols[i].at(row))));
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
  let text = "|" + names.map(escape2).join("|") + "|\n|" + names.map((name) => alignValue(align2[name])).join("|") + "|\n";
  scan(table2, names, options.limit, options.offset, {
    start() {
      text += "|";
    },
    cell(value2, name) {
      text += escape2(formatValue(value2, format[name])) + "|";
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
  groupby(...keys) {
    return groupby(this, ...keys);
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
  orderby(...keys) {
    return orderby(this, ...keys);
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
  dedupe(...keys) {
    return dedupe(this, ...keys);
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
  pivot(keys, values2, options) {
    return pivot(this, keys, values2, options);
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
    return union(this, ...tables);
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
    columnIndex: (name) => names.indexOf(name)
  }, columns2);
  const cols = columnSet();
  sel.forEach((name, key) => {
    const col = (
      /** @type {import('./types.js').ArrowColumn} */
      arrow.getChild(key)
    );
    cols.add(name, col.type.typeId === -1 ? dictionary(col) : col);
  });
  return new ColumnTable(cols.data, cols.names);
}
function dictionary(column) {
  const { data: data2, length, nullCount } = column;
  const batch = data2[data2.length - 1];
  const cache = batch.cache ?? batch.dictionary.toArray();
  const size = cache.length;
  const keys = dictKeys(data2, length, nullCount, size);
  const get2 = nullCount ? ((k) => k === size ? null : cache[k]) : ((k) => cache[k]);
  return {
    length,
    nullCount,
    at: (row) => get2(keys[row]),
    key: (row) => keys[row],
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
        keys,
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
function dictKeys(data2, length, nulls, size) {
  const v = data2.length > 1 || nulls ? flatten(data2, length) : data2[0].values;
  return nulls ? nullKeys(data2, v, size) : v;
}
function flatten(data2, length) {
  const type = data2[0].values.constructor;
  const array = new type(length);
  const n = data2.length;
  for (let i = 0, idx = 0, len; i < n; ++i) {
    len = data2[i].length;
    array.set(data2[i].values.subarray(0, len), idx);
    idx += len;
  }
  return array;
}
function nullKeys(data2, keys, key) {
  const n = data2.length;
  for (let i = 0, idx = 0, byte; i < n; ++i) {
    const batch = data2[i];
    const { length } = batch;
    const validity = batch.validity ?? batch.nullBitmap;
    const m = length >> 3;
    if (validity && validity.length) {
      for (let j = 0; j <= m; ++j) {
        if ((byte = validity[j]) !== 255) {
          const base = idx + (j << 3);
          if ((byte & 1 << 0) === 0) keys[base + 0] = key;
          if ((byte & 1 << 1) === 0) keys[base + 1] = key;
          if ((byte & 1 << 2) === 0) keys[base + 2] = key;
          if ((byte & 1 << 3) === 0) keys[base + 3] = key;
          if ((byte & 1 << 4) === 0) keys[base + 4] = key;
          if ((byte & 1 << 5) === 0) keys[base + 5] = key;
          if ((byte & 1 << 6) === 0) keys[base + 6] = key;
          if ((byte & 1 << 7) === 0) keys[base + 7] = key;
        }
      }
    }
    idx += length;
  }
  return keys;
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
  const raise = (type) => {
    error(`Illegal argument type: ${type || typeof values2}`);
    return (
      /** @type {import('./types.js').ColumnData} */
      {}
    );
  };
  return values2 instanceof Map ? fromKeyValuePairs(values2.entries(), names) : isDate(values2) ? raise("Date") : isRegExp(values2) ? raise("RegExp") : isString(values2) ? raise() : isArray(values2) ? fromArray(values2, names) : isFunction$1(values2[Symbol.iterator]) ? fromIterable(values2, names) : isObject$1(values2) ? fromKeyValuePairs(Object.entries(values2), names) : raise();
}
function fromKeyValuePairs(entries2, names = ["key", "value"]) {
  const keys = [];
  const vals = [];
  for (const [key, val] of entries2) {
    keys.push(key);
    vals.push(val);
  }
  const columns2 = {};
  if (names[0]) columns2[names[0]] = keys;
  if (names[1]) columns2[names[1]] = vals;
  return columns2;
}
function fromArray(values2, names) {
  const len = values2.length;
  const columns2 = {};
  const add = (name) => columns2[name] = Array(len);
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
  const add = (name) => columns2[name] = [];
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
  const keys = [];
  for (const [key, value2] of entries(columns2)) {
    data2[key] = value2;
    keys.push(key);
  }
  return new ColumnTable(data2, keys);
}
function from(values2, names) {
  return new ColumnTable(columnsFrom(values2, names), names);
}
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
async function expandResultsetRows(columnTable) {
  const colNames = columnTable.columnNames();
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
        const messageRefs = references.filter((ref) => ref.type === "message");
        const eventRefs = references.filter((ref) => ref.type === "event");
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
    () => selectedScanner ? data(selectedScanner) : void 0,
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
    transcriptMetadata,
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
      transcriptMetadata: transcriptMetadata || {},
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
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.validationTable), children: entries2.map(([key, value2]) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      Result,
      {
        value: value2,
        targetValue: valueStr(resolveTargetValue(target, key))
      }
    ) }, `validation-result-${key}`)) });
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
const resolveTargetValue = (target, key) => {
  if (target === void 0) {
    return "";
  }
  if (key === void 0) {
    return target;
  }
  if (target && typeof target === "object" && !Array.isArray(target)) {
    return target[key] || false;
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
        keysToDisplay.map((key, index) => {
          const displayValue = renderValue(
            index,
            value2[key],
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
                children: key
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles.valueValue), children: displayValue })
          ] }, `value-table-row-${key}`);
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
        id: `value-record-${summary.uuid}-${index}`,
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
    if (!summary?.uuid) {
      return (queryParams) => `?${queryParams}`;
    }
    return (queryParams) => {
      if (!scansDir) {
        return `?${queryParams}`;
      }
      const mergedParams = new URLSearchParams(currentSearchParams);
      const newParams = new URLSearchParams(queryParams);
      for (const [key, value2] of newParams) {
        mergedParams.set(key, value2);
      }
      return `#${scanResultRoute(scansDir, scanPath, summary.uuid, mergedParams)}`;
    };
  }, [summary?.uuid, scanPath, scansDir, currentSearchParams]);
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
  for (const ref of summary.messageReferences) {
    const renderPreview = refLookup[ref.id];
    const refUrl = makeReferenceUrl(ref.id, "message");
    if (ref.cite && (renderPreview || refUrl)) {
      refs.push({
        id: ref.id,
        cite: ref.cite,
        citePreview: renderPreview,
        citeUrl: refUrl
      });
    }
  }
  for (const ref of summary.eventReferences) {
    const renderPreview = refLookup[ref.id];
    const refUrl = makeReferenceUrl(ref.id, "event");
    if (ref.cite && (renderPreview || refUrl)) {
      refs.push({
        id: ref.id,
        cite: ref.cite,
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
  useSelectedScanner as f,
  useSelectedScanDataframe as g,
  useSelectedScan as h,
  getScanDisplayName as i,
  parseScanResultData as j,
  isTranscriptInput as k,
  isMessagesInput as l,
  isMessageInput as m,
  isEventsInput as n,
  isEventInput as o,
  parseScanResultSummaries as p,
  resultIdentifierStr as r,
  useMarkdownRefs as u
};
//# sourceMappingURL=refs.js.map
