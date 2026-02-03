import { describe, expect, it } from "vitest";

import { resolveAttachments } from "./attachmentsHelpers";

const attachments: Record<string, string> = {
  "00000000000000000000000000000001": "resolved_value_1",
  "00000000000000000000000000000002": "resolved_value_2",
  abcdef01234567890abcdef012345678: "another_resolved",
};

describe("resolveAttachments", () => {
  describe("primitives", () => {
    it.each([
      ["null", null, null],
      ["undefined", undefined, undefined],
      ["number", 42, 42],
      ["boolean true", true, true],
      ["boolean false", false, false],
    ])("passes through %s unchanged", (_, input, expected) => {
      expect(resolveAttachments(input, attachments)).toBe(expected);
    });
  });

  describe("strings", () => {
    it.each([
      ["no attachment ref", "plain text", "plain text"],
      ["partial match (short id)", "attachment://abc", "attachment://abc"],
      [
        "single ref",
        "attachment://00000000000000000000000000000001",
        "resolved_value_1",
      ],
      [
        "ref with surrounding text",
        "before attachment://00000000000000000000000000000001 after",
        "before resolved_value_1 after",
      ],
      [
        "multiple refs",
        "attachment://00000000000000000000000000000001 and attachment://00000000000000000000000000000002",
        "resolved_value_1 and resolved_value_2",
      ],
      [
        "unknown ref unchanged",
        "attachment://ffffffffffffffffffffffffffffffff",
        "attachment://ffffffffffffffffffffffffffffffff",
      ],
      [
        "mixed known and unknown",
        "attachment://00000000000000000000000000000001 attachment://ffffffffffffffffffffffffffffffff",
        "resolved_value_1 attachment://ffffffffffffffffffffffffffffffff",
      ],
    ])("%s", (_, input, expected) => {
      expect(resolveAttachments(input, attachments)).toBe(expected);
    });
  });

  describe("arrays", () => {
    it("resolves strings in array", () => {
      const input = [
        "attachment://00000000000000000000000000000001",
        "plain",
        "attachment://00000000000000000000000000000002",
      ];
      expect(resolveAttachments(input, attachments)).toEqual([
        "resolved_value_1",
        "plain",
        "resolved_value_2",
      ]);
    });

    it("preserves non-string elements", () => {
      const input = [1, true, null, "text"];
      expect(resolveAttachments(input, attachments)).toEqual([
        1,
        true,
        null,
        "text",
      ]);
    });

    it("handles nested arrays", () => {
      const input = [["attachment://00000000000000000000000000000001"]];
      expect(resolveAttachments(input, attachments)).toEqual([
        ["resolved_value_1"],
      ]);
    });
  });

  describe("objects", () => {
    it("resolves string values", () => {
      const input = {
        key: "attachment://00000000000000000000000000000001",
      };
      expect(resolveAttachments(input, attachments)).toEqual({
        key: "resolved_value_1",
      });
    });

    it("preserves non-string values", () => {
      const input = { num: 42, bool: true, nil: null };
      expect(resolveAttachments(input, attachments)).toEqual({
        num: 42,
        bool: true,
        nil: null,
      });
    });

    it("handles nested objects", () => {
      const input = {
        outer: {
          inner: "attachment://00000000000000000000000000000001",
        },
      };
      expect(resolveAttachments(input, attachments)).toEqual({
        outer: { inner: "resolved_value_1" },
      });
    });

    it("handles arrays inside objects", () => {
      const input = {
        items: ["attachment://00000000000000000000000000000001", "plain"],
      };
      expect(resolveAttachments(input, attachments)).toEqual({
        items: ["resolved_value_1", "plain"],
      });
    });

    it("handles objects inside arrays", () => {
      const input = [
        { text: "attachment://00000000000000000000000000000001" },
        { text: "plain" },
      ];
      expect(resolveAttachments(input, attachments)).toEqual([
        { text: "resolved_value_1" },
        { text: "plain" },
      ]);
    });
  });

  describe("deep nesting", () => {
    it("resolves at arbitrary depth", () => {
      const input = {
        a: {
          b: {
            c: [
              {
                d: "attachment://00000000000000000000000000000001",
              },
            ],
          },
        },
      };
      expect(resolveAttachments(input, attachments)).toEqual({
        a: { b: { c: [{ d: "resolved_value_1" }] } },
      });
    });
  });

  describe("empty attachments", () => {
    it("returns input unchanged when attachments empty", () => {
      const input = {
        text: "attachment://00000000000000000000000000000001",
      };
      expect(resolveAttachments(input, {})).toEqual({
        text: "attachment://00000000000000000000000000000001",
      });
    });
  });

  describe("type preservation", () => {
    it("preserves array type", () => {
      const input = ["a", "b"];
      const result = resolveAttachments(input, attachments);
      expect(Array.isArray(result)).toBe(true);
    });

    it("preserves object shape", () => {
      const input = { a: 1, b: "text" };
      const result = resolveAttachments(input, attachments);
      expect(Object.keys(result)).toEqual(["a", "b"]);
    });
  });
});
