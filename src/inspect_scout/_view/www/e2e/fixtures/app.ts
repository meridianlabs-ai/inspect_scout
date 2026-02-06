import {
  createNetworkFixture,
  type NetworkFixture,
} from "@msw/playwright";
import { test as base } from "@playwright/test";

import { defaultHandlers } from "./handlers";

/**
 * MockEventSource script injected via page.addInitScript().
 *
 * Immediately dispatches an SSE message with topic versions so the app's
 * useTopicInvalidation hook unblocks and the UI renders.
 */
const MOCK_EVENT_SOURCE_SCRIPT = `
  window.EventSource = class MockEventSource {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSED = 2;

    readyState = 0;
    onopen = null;
    onmessage = null;
    onerror = null;
    url;

    constructor(url) {
      this.url = url;
      // Transition to OPEN and dispatch initial topic versions on next microtask
      Promise.resolve().then(() => {
        this.readyState = 1;
        if (this.onopen) this.onopen(new Event("open"));
        if (this.onmessage) {
          this.onmessage(
            new MessageEvent("message", {
              data: JSON.stringify({ scans: "t1", "project-config": "p1" }),
            }),
          );
        }
      });
    }

    close() {
      this.readyState = 2;
    }

    addEventListener() {}
    removeEventListener() {}
    dispatchEvent() { return true; }
  };
`;

interface AppFixtures {
  network: NetworkFixture;
  disableRetries: void;
}

export const test = base.extend<AppFixtures>({
  // Override page to inject SSE mock before any navigation
  page: async ({ page }, use) => {
    await page.addInitScript(MOCK_EVENT_SOURCE_SCRIPT);
    await use(page); // eslint-disable-line react-hooks/rules-of-hooks
  },

  // Wire up MSW handlers via @msw/playwright
  network: createNetworkFixture({
    initialHandlers: defaultHandlers,
  }),

  // Opt-in fixture: destructure in a test to disable React Query retries
  disableRetries: [
    async ({ page }, use) => {
      await page.addInitScript(() => {
        globalThis.__TEST_DISABLE_RETRY = true;
      });
      await use();  
    },
    { auto: false },
  ],
});

export { expect } from "@playwright/test";
