import { EventSource } from "eventsource";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, vi } from "vitest";

// Node doesn't have EventSource — polyfill for MSW SSE support
Object.assign(globalThis, { EventSource });

// In browsers, console.groupCollapsed hides its content by default. Node has
// no concept of collapsing, so everything prints. This replicates the browser
// behavior: content inside collapsed groups is suppressed, while console.log
// calls outside of groups pass through normally. This quiets MSW's SSE handler
// (which wraps all its logging in groupCollapsed), but applies equally to any
// code that uses groupCollapsed.
let collapsedGroupDepth = 0;
const originalLog = console.log.bind(console);
vi.spyOn(console, "groupCollapsed").mockImplementation(() => {
  collapsedGroupDepth++;
});
vi.spyOn(console, "groupEnd").mockImplementation(() => {
  collapsedGroupDepth = Math.max(0, collapsedGroupDepth - 1);
});
vi.spyOn(console, "log").mockImplementation((...args: unknown[]) => {
  if (collapsedGroupDepth === 0) originalLog(...args);
});

export const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
