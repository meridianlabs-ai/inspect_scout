// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { getEmbeddedScanState } from "./embeddedState";

describe("getEmbeddedScanState", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("decodes URI-encoded characters in url", () => {
    vi.spyOn(document, "getElementById").mockReturnValue({
      textContent: JSON.stringify({
        type: "updateState",
        url: "/path/with%3Dequals/scan%3Dname",
      }),
    } as HTMLScriptElement);

    const result = getEmbeddedScanState();

    expect(result).toEqual({
      dir: "/path/with=equals",
      scan: "scan=name",
      scanner: undefined,
      extensionProtocolVersion: undefined,
    });
  });
});
